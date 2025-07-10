# Team Building AI Assistant

An intelligent team building system that analyzes project requirements and suggests optimal team compositions based on a comprehensive database of past projects and participants.

![Team Building AI](https://img.shields.io/badge/AI-Team%20Building-blue?style=flat-square)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104-green?style=flat-square)
![LangGraph](https://img.shields.io/badge/LangGraph-Latest-purple?style=flat-square)
![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector%20DB-orange?style=flat-square)

## 🚀 Features

- **AI-Powered Role Extraction**: Automatically identifies required roles from project descriptions
- **Semantic Project Search**: Uses vector similarity to find relevant past projects
- **Smart Team Suggestions**: Matches participants to roles based on skills and experience
- **Real-time Streaming**: Server-Sent Events (SSE) for live progress updates
- **Modern UI/UX**: Beautiful, responsive interface with gradient animations
- **Project Database Browser**: Explore 45+ project examples in an intuitive sidebar
- **One-Click Examples**: Pre-built prompts for common project types

## 🏗️ Architecture

### Core Components

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   FastAPI       │    │   LangGraph     │
│   (HTML/CSS/JS) │◄──►│   Server        │◄──►│   Workflow      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                       │
                                ▼                       ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │   ChromaDB      │    │   Upstage       │
                       │   Vector Store  │    │   LLM           │
                       └─────────────────┘    └─────────────────┘
```

### LangGraph Workflow

1. **Role Extraction**: Extract required roles from project description
2. **Query Paraphrasing**: Optimize search query for vector similarity
3. **Project Retrieval**: Find similar projects (iterative, max 2 rounds)
4. **Team Suggestion**: Match participants to extracted roles
5. **Completion Check**: Validate team composition and requirements

## 🛠️ Technology Stack

- **Backend**: FastAPI with async/await support
- **AI Framework**: LangGraph for workflow orchestration
- **LLM**: Upstage Solar-Pro for structured output generation
- **Vector Database**: ChromaDB for semantic project search
- **Embeddings**: Upstage embeddings for vector similarity
- **Frontend**: Vanilla JavaScript with modern CSS
- **Streaming**: Server-Sent Events (SSE) for real-time updates

## 📋 Prerequisites

- Python 3.9+
- Node.js (for development tools)
- Upstage API Key

## 🚀 Quick Start

### 1. Environment Setup

```bash
# Clone repository
cd examples/team_building

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Variables

Create a `.env` file in the project root:

```env
UPSTAGE_API_KEY=your_upstage_api_key_here
```

### 3. Initialize Vector Database

```bash
# This will create ChromaDB and populate with project data
python setup_chromadb.py
```

### 4. Start the Server

```bash
python server.py
```

The server will start at `http://localhost:8002`

### 5. Access the Application

Open your browser and navigate to `http://localhost:8002`

## 💡 Usage Examples

### Example Prompts (Try These!)

1. **AI Customer Service Platform**
   ```
   I need to build an AI-powered customer service platform for an e-commerce website. 
   The platform should include intelligent chatbots, automated order tracking, and 
   personalized product recommendations.
   ```

2. **Healthcare Data Management**
   ```
   I want to develop a healthcare data management platform that allows hospitals to 
   securely store patient records, track medical histories, and ensure HIPAA compliance.
   ```

3. **Personal Finance App**
   ```
   I need to create a personal finance management mobile app with AI-driven budgeting 
   recommendations, investment tracking, and financial goal setting.
   ```

### Custom Prompts

Describe any software project and the system will:
- Extract required roles (Project Manager, Developers, Designers, etc.)
- Find similar past projects
- Suggest team members with relevant experience
- Provide reasoning for each team member selection

## 🎨 UI Features

### Modern Design Elements
- **Gradient Header**: Beautiful purple-to-indigo gradient
- **Glass Morphism**: Subtle backdrop blur effects
- **Animated Interactions**: Smooth hover animations and transitions
- **Responsive Layout**: Works on desktop, tablet, and mobile
- **Progress Tracking**: Real-time workflow visualization

### Sidebar Project Browser
- **500px Width**: Optimized for project card display
- **Independent Scrolling**: Browse projects while using main interface
- **45+ Projects**: Comprehensive database of real project examples
- **Smart Filtering**: Easy to find relevant project patterns

### Example Prompt Bubbles
- **One-Click Activation**: Instant form filling and submission
- **Sliding Gradients**: Beautiful hover animations
- **Domain Coverage**: E-commerce, Healthcare, and FinTech examples

## 🔧 Configuration

### Server Settings
```python
# server.py
HOST = "0.0.0.0"
PORT = 8002
REQUEST_TIMEOUT = 300  # 5 minutes
```

### Retrieval Limits
```python
# graph/nodes.py
MAX_RETRIEVAL_ROUNDS = 2  # 10 documents total (5 per round)
DOCUMENTS_PER_ROUND = 5
```

### LLM Configuration
```python
# graph/upstage.py
MODEL = "solar-pro-250422"  # Upstage Solar Pro model
```

## 📊 Project Database

The system includes 45 pre-loaded projects across domains:
- **AI/Machine Learning** (58 specialists)
- **Healthcare & Medical** 
- **Financial Technology**
- **E-commerce & Retail**
- **Education Technology**
- **IoT & Smart Systems**
- **Cybersecurity**
- **Supply Chain & Logistics**

### Common Team Roles
- Backend Developers (20 projects)
- Frontend Developers (18 projects)
- Mobile App Developers (14 projects)
- UI/UX Designers (44 projects)
- AI Specialists (58 projects)
- Security Specialists (16 projects)
- Project Managers (most projects)

## 🎯 API Endpoints

### Health Check
```http
GET /health
```

### Team Building Stream
```http
GET /team-building/stream?message={project_description}&session_id={session_id}
```

### Static Files
```http
GET /static/{filename}
GET /
```

## 🧪 Development

### Project Structure
```
team_building/
├── server.py              # FastAPI server
├── setup_chromadb.py      # Database initialization
├── requirements.txt       # Python dependencies
├── static/
│   ├── index.html         # Main UI
│   ├── style.css          # Modern CSS styling
│   ├── script.js          # Frontend logic
│   └── projects_data_en.json  # Project database
├── graph/
│   ├── __init__.py
│   ├── nodes.py           # LangGraph workflow nodes
│   ├── schema.py          # Pydantic models
│   ├── state.py           # Workflow state management
│   └── upstage.py         # LLM integration
├── clients/
│   ├── chromadb.py        # Vector database client
│   └── upstage.py         # Upstage API client
└── embedding/
    └── upstage.py         # Embedding functions
```

### Adding New Projects

1. Edit `static/projects_data_en.json`
2. Add project with required schema:
   ```json
   {
     "project_name": "Your Project Name",
     "descriptive_summary": "Detailed description...",
     "required_roles": ["Role1", "Role2"],
     "duration_months": 12,
     "participants": [...]
   }
   ```
3. Re-run `python setup_chromadb.py`

### Customizing UI

- **Colors**: Edit CSS custom properties in `:root`
- **Animations**: Modify transition durations and easing functions
- **Layout**: Adjust sidebar width and responsive breakpoints
- **Examples**: Update prompts in `index.html`

## 🔍 Troubleshooting

### Common Issues

1. **Server won't start**
   ```bash
   # Check if port 8002 is in use
   lsof -i :8002
   # Kill existing processes
   pkill -f "python.*server.py"
   ```

2. **ChromaDB initialization fails**
   ```bash
   # Remove existing database and recreate
   rm -rf chromadb/
   python setup_chromadb.py
   ```

3. **LLM API errors**
   ```bash
   # Verify API key is set
   echo $UPSTAGE_API_KEY
   # Check API quota and status
   ```

4. **SSE connection issues**
   - Check browser developer tools for network errors
   - Verify server is running and accessible
   - Try refreshing the page

### Debug Mode

Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 📈 Performance

### Optimization Features
- **Streaming Responses**: Real-time progress updates
- **Vector Caching**: ChromaDB handles embedding cache
- **Iterative Retrieval**: Limited to 2 rounds for efficiency
- **Async Processing**: Non-blocking FastAPI operations

### Typical Response Times
- Role extraction: 2-3 seconds
- Project retrieval: 1-2 seconds per round
- Team suggestion: 3-5 seconds
- **Total**: 8-12 seconds for complete workflow

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

### Development Guidelines
- Follow existing code style
- Add type hints for new functions
- Update documentation for new features
- Test with multiple project types

## 📄 License

This project is part of the agentic-system examples collection.

## 🆘 Support

For issues and questions:
1. Check the troubleshooting section
2. Review server logs for errors
3. Test with example prompts first
4. Create an issue with detailed reproduction steps

---

**Built with ❤️ using LangGraph, FastAPI, and modern web technologies**