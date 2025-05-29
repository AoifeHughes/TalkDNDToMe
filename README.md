# Talk D&D To Me - Enhanced AI Dungeon Master

A sophisticated AI-powered Dungeon Master system for running Curse of Strahd campaigns with advanced features including dice rolling, character tracking, session management, and intelligent content retrieval.

## Features

- **Intelligent Content Loading**: Automatically loads and processes Curse of Strahd campaign materials with smart caching
- **Advanced Dice Rolling**: Comprehensive dice mechanics with automatic logging
- **Character Management**: Track player and NPC stats, inventory, relationships, and locations
- **Session Management**: Persistent session history and automatic summarization
- **RAG-Enhanced Responses**: Retrieval-Augmented Generation using campaign content and session history
- **Tool Integration**: OpenAI function calling for seamless game mechanics
- **Modular Architecture**: Clean, object-oriented design for easy customization and extension

## Project Structure

```
talk_dnd_to_me/
├── main.py                    # Entry point - run this to start the DM
├── requirements.txt           # Python dependencies
├── talk_dnd_to_me/
│   ├── config/
│   │   └── settings.py       # Configuration management
│   ├── core/
│   │   ├── dm_engine.py      # Main DM orchestrator
│   │   └── session_manager.py # Session lifecycle management
│   ├── database/
│   │   ├── chroma_client.py  # ChromaDB wrapper
│   │   └── cache_manager.py  # File caching logic
│   ├── content/
│   │   ├── content_loader.py # Document loading and processing
│   │   └── embeddings.py     # Embedding generation
│   ├── game/
│   │   ├── dice.py          # Dice rolling functionality
│   │   ├── character_manager.py # Character tracking
│   │   └── tools.py         # Game tool definitions
│   ├── ai/
│   │   ├── llm_client.py    # OpenAI/LLM client wrapper
│   │   └── context_retriever.py # RAG context retrieval
│   └── utils/
│       └── file_utils.py    # File utilities
```

## Installation

1. **Clone the repository** (if applicable) or ensure you have all the files in the correct structure.

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Ensure you have the Curse of Strahd content**:
   - Place your `Curse-of-Strahd-Reloaded` directory in the project root
   - Or update the content directory path in the configuration

4. **Set up your LLM server**:
   - The system is configured for llama.cpp by default (localhost:11434)
   - Update the AI configuration if using a different setup

## Usage

### Basic Usage

Simply run the main script:

```bash
python main.py
```

This will:
1. Initialize all subsystems
2. Load and process campaign content
3. Start an interactive chat session with the AI DM

### Customization

You can customize the system by modifying the configuration in `main.py`:

```python
from talk_dnd_to_me.config.settings import DMConfig

# Create custom configuration
config = DMConfig.default()

# Customize content directory
config.update_content_directory("path/to/your/content")

# Customize AI settings
config.update_ai_settings(
    base_url="http://your-llm-server:port/v1",
    temperature=0.8,
    model_name="your-model"
)

# Use custom configuration
dm_engine = DMEngine(config)
```

### Advanced Usage

For more advanced customization, you can:

1. **Extend the DMEngine class** to add new functionality
2. **Create custom tool handlers** by extending GameToolHandler
3. **Add new content loaders** for different campaign materials
4. **Implement custom character management** logic

## Configuration Options

### Database Configuration
- Collection names for different data types
- ChromaDB settings

### Content Configuration
- Content directory path
- Text chunking parameters
- Context retrieval limits

### AI Configuration
- LLM server URL and API key
- Model parameters (temperature, max tokens)
- Embedding model selection

### Game Configuration
- Dice rolling limits and valid dice types
- Conversation history management
- Session settings

## Game Features

### Dice Rolling
- Supports all standard D&D dice (d4, d6, d8, d10, d12, d20, d100)
- Automatic modifier application
- Roll history tracking
- Integration with character sheets

### Character Management
- HP tracking (current/maximum)
- Inventory management
- Location tracking
- Relationship mapping
- Automatic change logging

### Session Management
- Unique session IDs
- Comprehensive history logging
- Automatic session summaries
- Cross-session character persistence

## Commands

During a session, you can:
- **Chat naturally** with the AI DM
- **Type 'quit', 'exit', or 'END SESSION'** to end the session
- The DM will automatically roll dice when needed
- Character stats and story progress are tracked automatically

## Technical Details

### Architecture Benefits
- **Separation of Concerns**: Each module has a single responsibility
- **Configurability**: Easy to customize behavior through class parameters
- **Testability**: Individual components can be unit tested
- **Maintainability**: Easier to modify specific functionality
- **Extensibility**: Simple to add new game tools or content sources

### Performance Features
- **Smart Caching**: Only processes changed files
- **Efficient Embeddings**: Reuses embeddings for unchanged content
- **Optimized Retrieval**: Configurable context limits
- **Session Management**: Efficient conversation history handling

## Migration from model_runner.py

This refactored version maintains 100% compatibility with the original `model_runner.py` functionality while providing:
- Better code organization
- Easier customization
- Improved maintainability
- Enhanced extensibility

The main entry point (`main.py`) provides the same `chat_with_dm()` experience as before, but now with a clean, modular architecture underneath.

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure all files are in the correct directory structure
2. **Missing Dependencies**: Run `pip install -r requirements.txt`
3. **Content Not Found**: Check that the Curse-of-Strahd-Reloaded directory exists
4. **LLM Connection Issues**: Verify your LLM server is running and accessible
5. **Embedding Model Issues**: Install sentence-transformers: `pip install sentence-transformers`

### Debug Mode

For debugging, you can add print statements or logging to any module. The modular structure makes it easy to isolate and debug specific functionality.

## Contributing

The modular architecture makes it easy to contribute:
1. **Add new game tools** in the `game/` directory
2. **Extend AI capabilities** in the `ai/` directory
3. **Add new content loaders** in the `content/` directory
4. **Improve database operations** in the `database/` directory

## License

[Add your license information here]
