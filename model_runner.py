import os
import chromadb
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.schema import Document
from openai import OpenAI
import sys
import glob
import hashlib
import json
import random
from datetime import datetime
import uuid

# Suppress tokenizers parallelism warning
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Setup OpenAI client for llama.cpp
client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="sk-xxxxxxxxxxxxxxxx"  # placeholder, not used by llama.cpp
)

# Global variables for collections
chroma_client = None
content_collection = None
history_collection = None
character_collection = None
cache_collection = None
embedding_model = None
current_session_id = None

def get_file_hash(file_path):
    """Calculate SHA256 hash of a file"""
    hash_sha256 = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    except Exception as e:
        print(f"Error hashing file {file_path}: {e}")
        return None

def check_file_cache(file_path):
    """Check if file is cached and unchanged"""
    try:
        current_hash = get_file_hash(file_path)
        if not current_hash:
            return False
        
        # Check if cache collection has any documents first
        try:
            cache_id = f"cache_{hashlib.md5(file_path.encode()).hexdigest()}"
            results = cache_collection.get(ids=[cache_id])
            
            if results['documents'] and len(results['documents']) > 0:
                cached_data = json.loads(results['documents'][0])
                return cached_data.get('file_hash') == current_hash
            return False
        except Exception:
            # If cache entry doesn't exist, return False
            return False
            
    except Exception as e:
        print(f"Error checking cache for {file_path}: {e}")
        return False

def update_file_cache(file_path, file_hash, chunk_ids, metadata):
    """Update file cache with new hash and chunk references"""
    try:
        cache_data = {
            "file_path": file_path,
            "file_hash": file_hash,
            "last_modified": datetime.now().isoformat(),
            "chunk_ids": chunk_ids,
            "metadata": metadata
        }
        
        # Remove existing cache entry
        try:
            cache_collection.delete(where={"file_path": file_path})
        except:
            pass
        
        # Add new cache entry
        cache_collection.add(
            documents=[json.dumps(cache_data)],
            metadatas=[{"file_path": file_path, "last_modified": cache_data["last_modified"]}],
            ids=[f"cache_{hashlib.md5(file_path.encode()).hexdigest()}"]
        )
        print(f"✓ Updated cache for {os.path.basename(file_path)}")
    except Exception as e:
        print(f"Error updating cache for {file_path}: {e}")

def load_curse_of_strahd_content():
    """Load all markdown files from Curse of Strahd with smart caching"""
    base_path = "Curse-of-Strahd-Reloaded"
    
    if not os.path.exists(base_path):
        print(f"✗ Error: Path '{base_path}' does not exist")
        sys.exit(1)
    
    # Find all markdown files recursively
    md_files = []
    for root, dirs, files in os.walk(base_path):
        for file in files:
            if file.endswith('.md'):
                md_files.append(os.path.join(root, file))
    
    if not md_files:
        print(f"✗ No markdown files found in '{base_path}'")
        sys.exit(1)
    
    print(f"Found {len(md_files)} markdown files")
    
    documents = []
    files_to_process = []
    cached_chunks = []
    
    # Check which files need processing
    for file_path in md_files:
        if check_file_cache(file_path):
            print(f"✓ Using cached version of {os.path.basename(file_path)}")
            # Load cached chunk IDs and add to existing chunks
            try:
                results = cache_collection.query(
                    query_embeddings=None,
                    where={"file_path": file_path},
                    n_results=1
                )
                if results['documents'] and len(results['documents'][0]) > 0:
                    cached_data = json.loads(results['documents'][0][0])
                    cached_chunks.extend(cached_data.get('chunk_ids', []))
            except Exception as e:
                print(f"Warning: Error loading cached chunks for {file_path}: {e}")
                files_to_process.append(file_path)
        else:
            files_to_process.append(file_path)
    
    print(f"Processing {len(files_to_process)} new/changed files, using {len(cached_chunks)} cached chunks")
    
    # Process new/changed files
    for file_path in files_to_process:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract metadata from path
            rel_path = os.path.relpath(file_path, base_path)
            path_parts = rel_path.split(os.sep)
            
            filename = os.path.basename(file_path)
            filename_no_ext = os.path.splitext(filename)[0]
            
            # Determine act and content type from path
            act = "Unknown"
            act_number = "0"
            if len(path_parts) > 0 and "Act" in path_parts[0]:
                act = path_parts[0]
                act_number = act.split()[1] if len(act.split()) > 1 else "0"
            
            # Create document with enhanced metadata
            doc = Document(
                page_content=content,
                metadata={
                    "source": file_path,
                    "filename": filename,
                    "act": act,
                    "act_number": act_number,
                    "document_type": "curse_of_strahd",
                    "content_type": filename_no_ext,
                    "relative_path": rel_path
                }
            )
            
            # Prepend context to content for better embedding
            enhanced_content = f"[{act}] {filename_no_ext}\n\n{content}"
            doc.page_content = enhanced_content
            
            documents.append(doc)
            print(f"✓ Loaded {filename} ({len(content)} characters)")
            
        except Exception as e:
            print(f"✗ Error loading {file_path}: {e}")
            continue
    
    return documents, files_to_process

def setup_collections():
    """Initialize all ChromaDB collections"""
    global chroma_client, content_collection, history_collection, character_collection, cache_collection
    
    print("Setting up ChromaDB collections...")
    try:
        chroma_client = chromadb.Client()
        
        # Create or get collections
        try:
            content_collection = chroma_client.get_collection("curse_of_strahd_content")
            print("✓ Using existing content collection")
        except:
            content_collection = chroma_client.create_collection("curse_of_strahd_content")
            print("✓ Created content collection")
        
        try:
            history_collection = chroma_client.get_collection("campaign_history")
            print("✓ Using existing history collection")
        except:
            history_collection = chroma_client.create_collection("campaign_history")
            print("✓ Created history collection")
        
        try:
            character_collection = chroma_client.get_collection("character_data")
            print("✓ Using existing character collection")
        except:
            character_collection = chroma_client.create_collection("character_data")
            print("✓ Created character collection")
        
        try:
            cache_collection = chroma_client.get_collection("file_cache")
            print("✓ Using existing cache collection")
        except:
            cache_collection = chroma_client.create_collection("file_cache")
            print("✓ Created cache collection")
            
    except Exception as e:
        print(f"✗ Error setting up ChromaDB: {e}")
        sys.exit(1)

def process_documents(documents, files_to_process):
    """Process and embed new documents"""
    if not documents:
        print("No new documents to process")
        return
    
    print(f"\nSplitting {len(documents)} documents into chunks...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, 
        chunk_overlap=200,
        separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""]
    )

    # Split documents while preserving metadata
    all_chunks = []
    file_chunk_mapping = {}
    
    for doc in documents:
        chunks = text_splitter.split_documents([doc])
        file_path = doc.metadata['source']
        chunk_ids = []
        
        for i, chunk in enumerate(chunks):
            chunk_id = f"chunk_{hashlib.md5((file_path + str(i)).encode()).hexdigest()}"
            chunk.metadata['chunk_id'] = chunk_id
            chunk_ids.append(chunk_id)
            all_chunks.append(chunk)
        
        file_chunk_mapping[file_path] = chunk_ids

    print(f"✓ Created {len(all_chunks)} chunks from {len(documents)} documents")

    if len(all_chunks) == 0:
        print("✗ No chunks were created")
        return

    print("Generating embeddings...")
    try:
        chunk_texts = [chunk.page_content for chunk in all_chunks]
        embeddings = embedding_model.embed_documents(chunk_texts)
        print(f"✓ Generated {len(embeddings)} embeddings")
    except Exception as e:
        print(f"✗ Error generating embeddings: {e}")
        return

    print("Storing chunks in ChromaDB...")
    try:
        # Prepare metadata for ChromaDB
        metadatas = []
        chunk_ids = []
        
        for chunk in all_chunks:
            metadata = {
                "source": chunk.metadata.get("source", ""),
                "filename": chunk.metadata.get("filename", ""),
                "act": chunk.metadata.get("act", ""),
                "act_number": chunk.metadata.get("act_number", ""),
                "document_type": chunk.metadata.get("document_type", ""),
                "content_type": chunk.metadata.get("content_type", ""),
                "chunk_id": chunk.metadata.get("chunk_id", "")
            }
            metadatas.append(metadata)
            chunk_ids.append(chunk.metadata.get("chunk_id", ""))
        
        # Remove existing chunks for updated files
        for file_path in files_to_process:
            try:
                content_collection.delete(where={"source": file_path})
            except:
                pass
        
        # Add new chunks
        content_collection.add(
            embeddings=embeddings,
            documents=chunk_texts,
            metadatas=metadatas,
            ids=chunk_ids
        )
        print(f"✓ Stored {len(all_chunks)} chunks in database")
        
        # Update file cache
        for file_path in files_to_process:
            file_hash = get_file_hash(file_path)
            if file_hash and file_path in file_chunk_mapping:
                # Find the document metadata for this file
                doc_metadata = next((doc.metadata for doc in documents if doc.metadata['source'] == file_path), {})
                update_file_cache(file_path, file_hash, file_chunk_mapping[file_path], doc_metadata)
        
    except Exception as e:
        print(f"✗ Error storing in ChromaDB: {e}")

# Tool Functions
def roll_dice(number_of_dice, dice_type, modification_int=0):
    """Roll dice and return formatted result"""
    if dice_type not in [4, 6, 8, 10, 12, 20, 100]:
        return f"❌ Invalid dice type: d{dice_type}. Valid types: d4, d6, d8, d10, d12, d20, d100"
    
    if number_of_dice < 1 or number_of_dice > 20:
        return f"❌ Invalid number of dice: {number_of_dice}. Must be between 1 and 20"
    
    rolls = [random.randint(1, dice_type) for _ in range(number_of_dice)]
    total = sum(rolls) + modification_int
    
    # Format the result
    rolls_str = ", ".join(map(str, rolls))
    if number_of_dice == 1:
        if modification_int != 0:
            result = f"🎲 Rolling 1d{dice_type}{modification_int:+d}: [{rolls[0]}] {modification_int:+d} = {total}"
        else:
            result = f"🎲 Rolling 1d{dice_type}: [{rolls[0]}] = {total}"
    else:
        if modification_int != 0:
            result = f"🎲 Rolling {number_of_dice}d{dice_type}{modification_int:+d}: [{rolls_str}] {modification_int:+d} = {total}"
        else:
            result = f"🎲 Rolling {number_of_dice}d{dice_type}: [{rolls_str}] = {total}"
    
    # Log the roll to session history
    log_to_session({
        "entry_type": "dice_roll",
        "content": result,
        "dice_data": {
            "expression": f"{number_of_dice}d{dice_type}{modification_int:+d}" if modification_int != 0 else f"{number_of_dice}d{dice_type}",
            "rolls": rolls,
            "modifier": modification_int,
            "total": total
        }
    })
    
    return result

def update_character(character_name, update_type, update_data):
    """Update character information"""
    try:
        character_id = f"char_{character_name.lower().replace(' ', '_')}"
        
        # Try to get existing character
        results = character_collection.query(
            query_embeddings=None,
            where={"character_id": character_id},
            n_results=1
        )
        
        if results['documents'] and len(results['documents'][0]) > 0:
            character_data = json.loads(results['documents'][0][0])
        else:
            # Create new character
            character_data = {
                "character_id": character_id,
                "name": character_name,
                "character_type": "unknown",
                "last_updated": datetime.now().isoformat(),
                "session_last_seen": current_session_id,
                "attributes": {},
                "inventory": {},
                "personality": {},
                "relationships": {},
                "campaign_data": {},
                "change_log": []
            }
        
        # Apply update based on type
        if update_type == "hp":
            if "attributes" not in character_data:
                character_data["attributes"] = {}
            if "hit_points" not in character_data["attributes"]:
                character_data["attributes"]["hit_points"] = {"current": 0, "maximum": 0}
            
            if "current" in update_data:
                character_data["attributes"]["hit_points"]["current"] = update_data["current"]
            if "maximum" in update_data:
                character_data["attributes"]["hit_points"]["maximum"] = update_data["maximum"]
                
        elif update_type == "inventory":
            character_data["inventory"].update(update_data)
            
        elif update_type == "status":
            character_data["campaign_data"].update(update_data)
            
        elif update_type == "relationship":
            character_data["relationships"].update(update_data)
            
        elif update_type == "location":
            if "campaign_data" not in character_data:
                character_data["campaign_data"] = {}
            character_data["campaign_data"]["current_location"] = update_data.get("location", "")
        
        # Add to change log
        character_data["change_log"].append({
            "timestamp": datetime.now().isoformat(),
            "change": f"Updated {update_type}: {update_data}",
            "session": current_session_id
        })
        
        character_data["last_updated"] = datetime.now().isoformat()
        character_data["session_last_seen"] = current_session_id
        
        # Save updated character
        try:
            character_collection.delete(where={"character_id": character_id})
        except:
            pass
        
        character_collection.add(
            documents=[json.dumps(character_data)],
            metadatas=[{
                "character_id": character_id,
                "character_name": character_name,
                "character_type": character_data.get("character_type", "unknown"),
                "last_updated": character_data["last_updated"]
            }],
            ids=[character_id]
        )
        
        return f"✓ Updated {character_name}: {update_type} = {update_data}"
        
    except Exception as e:
        return f"❌ Error updating character {character_name}: {e}"

def get_character_info(character_name):
    """Retrieve character information"""
    try:
        character_id = f"char_{character_name.lower().replace(' ', '_')}"
        
        results = character_collection.query(
            query_embeddings=None,
            where={"character_id": character_id},
            n_results=1
        )
        
        if results['documents'] and len(results['documents'][0]) > 0:
            character_data = json.loads(results['documents'][0][0])
            
            # Format character info for display
            info = f"📋 **{character_data['name']}**\n"
            
            if "attributes" in character_data and character_data["attributes"]:
                info += "**Stats:** "
                attrs = character_data["attributes"]
                if "hit_points" in attrs:
                    hp = attrs["hit_points"]
                    info += f"HP: {hp.get('current', '?')}/{hp.get('maximum', '?')} "
                if "armor_class" in attrs:
                    info += f"AC: {attrs['armor_class']} "
                if "level" in attrs:
                    info += f"Level: {attrs['level']} "
                info += "\n"
            
            if "campaign_data" in character_data and "current_location" in character_data["campaign_data"]:
                info += f"**Location:** {character_data['campaign_data']['current_location']}\n"
            
            if "inventory" in character_data and character_data["inventory"]:
                info += f"**Inventory:** {character_data['inventory']}\n"
            
            return info
        else:
            return f"❌ Character '{character_name}' not found"
            
    except Exception as e:
        return f"❌ Error retrieving character {character_name}: {e}"

def end_session():
    """End the current session and create a summary"""
    global current_session_id
    
    try:
        # Get all entries from current session
        results = history_collection.query(
            query_embeddings=None,
            where={"session_id": current_session_id},
            n_results=1000  # Get all entries
        )
        
        if results['documents'] and len(results['documents'][0]) > 0:
            session_entries = [json.loads(doc) for doc in results['documents'][0]]
            
            # Create session summary
            summary = {
                "session_id": current_session_id,
                "timestamp": datetime.now().isoformat(),
                "entry_type": "session_summary",
                "content": f"Session {current_session_id} ended",
                "session_data": {
                    "total_entries": len(session_entries),
                    "dice_rolls": [entry for entry in session_entries if entry.get("entry_type") == "dice_roll"],
                    "key_events": [entry for entry in session_entries if entry.get("entry_type") in ["player_input", "dm_response"]]
                }
            }
            
            # Save session summary
            summary_id = f"summary_{current_session_id}"
            history_collection.add(
                documents=[json.dumps(summary)],
                metadatas=[{
                    "session_id": current_session_id,
                    "entry_type": "session_summary",
                    "timestamp": summary["timestamp"]
                }],
                ids=[summary_id]
            )
            
            return f"✓ Session {current_session_id} ended. Summary saved with {len(session_entries)} entries."
        else:
            return f"✓ Session {current_session_id} ended (no entries found)."
            
    except Exception as e:
        return f"❌ Error ending session: {e}"

def log_to_session(entry_data):
    """Log an entry to the current session history"""
    global current_session_id
    
    if not current_session_id:
        return
    
    try:
        entry = {
            "session_id": current_session_id,
            "timestamp": datetime.now().isoformat(),
            "entry_id": str(uuid.uuid4()),
            **entry_data
        }
        
        entry_id = f"entry_{entry['entry_id']}"
        
        history_collection.add(
            documents=[json.dumps(entry)],
            metadatas=[{
                "session_id": current_session_id,
                "entry_type": entry.get("entry_type", "unknown"),
                "timestamp": entry["timestamp"]
            }],
            ids=[entry_id]
        )
        
    except Exception as e:
        print(f"Warning: Error logging to session: {e}")

def get_relevant_context(query, max_chunks=5):
    """Retrieve relevant context from knowledge base and session history"""
    try:
        query_embedding = embedding_model.embed_query(query)
        
        # Get context from campaign content
        content_results = content_collection.query(
            query_embeddings=[query_embedding],
            n_results=min(max_chunks, 3),
            include=["documents", "metadatas"]
        )
        
        # Get context from session history
        history_results = history_collection.query(
            query_embeddings=[query_embedding],
            n_results=min(max_chunks, 2),
            include=["documents", "metadatas"]
        )
        
        context_parts = []
        
        # Add campaign content
        if content_results['documents'][0]:
            for doc, metadata in zip(content_results['documents'][0], content_results['metadatas'][0]):
                context_parts.append(f"[Campaign Content - {metadata['content_type']}] {doc}")
        
        # Add session history
        if history_results['documents'][0]:
            for doc, metadata in zip(history_results['documents'][0], history_results['metadatas'][0]):
                entry = json.loads(doc)
                if entry.get('entry_type') in ['player_input', 'dm_response', 'dice_roll']:
                    context_parts.append(f"[Session History] {entry.get('content', '')}")
        
        return "\n\n".join(context_parts)
        
    except Exception as e:
        print(f"Warning: Error retrieving context: {e}")
        return ""

# Tool definitions for OpenAI
tools = [
    {
        "type": "function",
        "function": {
            "name": "roll_dice",
            "description": "Roll dice for D&D gameplay. Use this when players need to make ability checks, attack rolls, damage rolls, or any other dice-based mechanics.",
            "parameters": {
                "type": "object",
                "properties": {
                    "number_of_dice": {
                        "type": "integer",
                        "description": "Number of dice to roll (1-20)"
                    },
                    "dice_type": {
                        "type": "integer",
                        "description": "Type of dice (4, 6, 8, 10, 12, 20, 100)",
                        "enum": [4, 6, 8, 10, 12, 20, 100]
                    },
                    "modification_int": {
                        "type": "integer",
                        "description": "Modifier to add or subtract from the roll (default 0)",
                        "default": 0
                    }
                },
                "required": ["number_of_dice", "dice_type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_character",
            "description": "Update character stats, inventory, status, or other information",
            "parameters": {
                "type": "object",
                "properties": {
                    "character_name": {
                        "type": "string",
                        "description": "Name of the character to update"
                    },
                    "update_type": {
                        "type": "string",
                        "description": "Type of update to perform",
                        "enum": ["hp", "inventory", "status", "relationship", "location"]
                    },
                    "update_data": {
                        "type": "object",
                        "description": "Data to update (structure depends on update_type)"
                    }
                },
                "required": ["character_name", "update_type", "update_data"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_character_info",
            "description": "Retrieve current information about a character or NPC",
            "parameters": {
                "type": "object",
                "properties": {
                    "character_name": {
                        "type": "string",
                        "description": "Name of the character to look up"
                    }
                },
                "required": ["character_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "end_session",
            "description": "End the current D&D session and create a summary",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    }
]

def handle_tool_calls(tool_calls):
    """Execute tool calls and return results"""
    results = []
    
    for tool_call in tool_calls:
        function_name = tool_call.function.name
        arguments = json.loads(tool_call.function.arguments)
        
        try:
            if function_name == "roll_dice":
                result = roll_dice(
                    arguments.get("number_of_dice"),
                    arguments.get("dice_type"),
                    arguments.get("modification_int", 0)
                )
            elif function_name == "update_character":
                result = update_character(
                    arguments.get("character_name"),
                    arguments.get("update_type"),
                    arguments.get("update_data")
                )
            elif function_name == "get_character_info":
                result = get_character_info(arguments.get("character_name"))
            elif function_name == "end_session":
                result = end_session()
            else:
                result = f"❌ Unknown function: {function_name}"
                
        except Exception as e:
            result = f"❌ Error executing {function_name}: {e}"
        
        results.append({
            "tool_call_id": tool_call.id,
            "role": "tool",
            "content": result
        })
    
    return results

def chat_with_dm():
    """Interactive chat loop with the enhanced DM"""
    global current_session_id
    
    # Start new session
    current_session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    print("\n" + "="*60)
    print("🎲 ENHANCED CURSE OF STRAHD - DUNGEON MASTER 🎲")
    print("="*60)
    print("Welcome to Barovia! I'm your enhanced AI Dungeon Master.")
    print("I can roll dice, track characters, and remember everything!")
    print(f"\nSession ID: {current_session_id}")
    print("\nCommands:")
    print("- Type 'quit', 'exit', or 'END SESSION' to end")
    print("- I can roll dice automatically when needed")
    print("- I'll track character stats and story progress")
    print("-" * 60)
    
    # Initialize conversation history
    conversation_history = [{
        "role": "system",
        "content": """You are an expert Dungeon Master running Curse of Strahd: Reloaded with enhanced capabilities. You have access to tools for dice rolling, character management, and session tracking.

Your enhanced abilities:
- Roll dice using the roll_dice function when players need checks, saves, attacks, or damage
- Update character information using update_character when stats change
- Look up character details using get_character_info when needed
- End sessions properly using end_session when requested

Your role:
- Act as an engaging, atmospheric DM who brings Barovia to life
- Use dice rolls naturally in gameplay (ability checks, combat, etc.)
- Track character changes (HP, inventory, relationships, location)
- Reference past events and character details from memory
- Create tension and atmosphere appropriate to the horror setting
- Guide players through the story while letting them make meaningful choices

Always be immersive and interactive. Use your tools to enhance the gameplay experience."""
    }]
    
    # Log session start
    log_to_session({
        "entry_type": "session_start",
        "content": f"Started new D&D session: {current_session_id}"
    })
    
    while True:
        try:
            # Get user input
            user_input = input("\n🎭 You: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'q', 'end session']:
                print("\n🌙 Ending session...")
                end_result = end_session()
                print(end_result)
                print("The mists of Barovia fade as you step back into reality...")
                print("Thanks for playing! May you find your way out of the darkness.")
                break
            
            if not user_input:
                continue
            
            # Log player input
            log_to_session({
                "entry_type": "player_input",
                "content": user_input
            })
            
            # Get relevant context from the knowledge base
            context = get_relevant_context(user_input, max_chunks=3)
            
            # Prepare the prompt with context
            context_prompt = ""
            if context:
                context_prompt = f"\n\nRelevant information:\n{context}"
            
            # Add user message to conversation
            conversation_history.append({
                "role": "user",
                "content": user_input + context_prompt
            })
            
            # Keep conversation history manageable (last 10 messages)
            if len(conversation_history) > 11:  # system + 10 messages
                conversation_history = [conversation_history[0]] + conversation_history[-10:]
            
            print("\n🎲 DM: ", end="", flush=True)
            
            # Generate DM response with tool calling
            response = client.chat.completions.create(
                model="llama.cpp",
                messages=conversation_history,
                tools=tools,
                tool_choice="auto",
                temperature=0.7,
                max_tokens=500
            )
            
            response_message = response.choices[0].message
            
            # Handle tool calls if present
            if response_message.tool_calls:
                # Add the assistant's message with tool calls to conversation
                conversation_history.append({
                    "role": "assistant",
                    "content": response_message.content,
                    "tool_calls": [{
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    } for tc in response_message.tool_calls]
                })
                
                # Execute tool calls
                tool_results = handle_tool_calls(response_message.tool_calls)
                
                # Display tool results to user
                for result in tool_results:
                    print(result["content"])
                
                # Add tool results to conversation
                conversation_history.extend(tool_results)
                
                # Get final response after tool execution
                final_response = client.chat.completions.create(
                    model="llama.cpp",
                    messages=conversation_history,
                    temperature=0.7,
                    max_tokens=500
                )
                
                dm_response = final_response.choices[0].message.content
                print(dm_response)
                
                # Log DM response
                log_to_session({
                    "entry_type": "dm_response",
                    "content": dm_response
                })
                
                # Add final DM response to conversation history
                conversation_history.append({
                    "role": "assistant",
                    "content": dm_response
                })
                
            else:
                # No tool calls, just regular response
                dm_response = response_message.content
                print(dm_response)
                
                # Log DM response
                log_to_session({
                    "entry_type": "dm_response",
                    "content": dm_response
                })
                
                # Add DM response to conversation history
                conversation_history.append({
                    "role": "assistant",
                    "content": dm_response
                })
            
        except KeyboardInterrupt:
            print("\n\n🌙 Session interrupted. The mists swirl around you...")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            print("The mists seem to interfere with our connection. Try again...")

# Main execution
if __name__ == "__main__":
    print("🎲 Enhanced Curse of Strahd DM System Starting...")
    
    # Initialize embedding model
    print("\nInitializing embedding model...")
    try:
        embedding_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        print("✓ Embedding model loaded successfully")
    except Exception as e:
        print(f"✗ Error loading embedding model: {e}")
        print("Try installing: pip install sentence-transformers")
        sys.exit(1)
    
    # Setup ChromaDB collections
    setup_collections()
    
    # Load and process documents with smart caching
    print("\nLoading Curse of Strahd content...")
    try:
        documents, files_to_process = load_curse_of_strahd_content()
        if documents:
            process_documents(documents, files_to_process)
        print(f"✓ Content loading complete")
    except Exception as e:
        print(f"✗ Error loading content: {e}")
        sys.exit(1)
    
    # Test retrieval
    print("\nTesting enhanced system...")
    test_context = get_relevant_context("What is Death House?")
    if test_context:
        print("✓ Context retrieval working")
    else:
        print("⚠ Warning: Context retrieval may not be working properly")
    
    print("\n✓ All systems ready! Starting enhanced DM session...")
    
    # Start the interactive chat
    chat_with_dm()
