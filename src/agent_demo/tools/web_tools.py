# FILE: src/agent_demo/tools/web_tools.py
import os
import json
from crewai.tools import BaseTool
from typing import Optional

class CodeGeneratorTool(BaseTool):
    """Tool for generating code snippets and templates"""
    name: str = "CodeGenerator"
    description: str = "Generates code templates and snippets for web development projects"

    def _run(self, language: str, component_type: str, component_name: str, features: Optional[str] = None) -> str:
        try:
            if language.lower() == "react":
                return self._generate_react_component(component_name, features)
            elif language.lower() == "html":
                return self._generate_html_template(component_name, features)
            elif language.lower() == "css":
                return self._generate_css_styles(component_name, features)
            elif language.lower() == "javascript":
                return self._generate_js_module(component_name, features)
            elif language.lower() == "nodejs":
                return self._generate_node_server(component_name, features)
            else:
                return f"Language {language} not supported. Supported: react, html, css, javascript, nodejs"
        except Exception as e:
            return f"Error generating code: {str(e)}"
    
    def _generate_react_component(self, name: str, features: str) -> str:
        component_template = f'''import React, {{ useState, useEffect }} from 'react';
import './styles/{name}.css';

const {name} = () => {{
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {{
    // Initialize component
    fetchData();
  }}, []);

  const fetchData = async () => {{
    setLoading(true);
    try {{
      // Fetch data logic here
      const response = await fetch('/api/{name.lower()}');
      const result = await response.json();
      setData(result);
    }} catch (error) {{
      console.error('Error fetching data:', error);
    }} finally {{
      setLoading(false);
    }}
  }};

  if (loading) return <div className="loading">Loading...</div>;

  return (
    <div className="{name.lower()}-container">
      <h2>{name} Component</h2>
      {{/* Component content */}}
      <div className="content">
        {{data.length > 0 ? (
          <ul>
            {{data.map((item, index) => (
              <li key={{index}}>{{item.name}}</li>
            ))}}
          </ul>
        ) : (
          <p>No data available</p>
        )}}
      </div>
    </div>
  );
}};

export default {name};'''
        return component_template
    
    def _generate_html_template(self, name: str, features: str) -> str:
        html_template = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{name}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="styles/{name.lower()}.css">
</head>
<body>
    <div class="container-fluid">
        <header class="navbar navbar-expand-lg navbar-dark bg-dark">
            <div class="container">
                <a class="navbar-brand" href="#">{name}</a>
                <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                    <span class="navbar-toggler-icon"></span>
                </button>
                <div class="collapse navbar-collapse" id="navbarNav">
                    <ul class="navbar-nav ms-auto">
                        <li class="nav-item"><a class="nav-link" href="#home">Home</a></li>
                        <li class="nav-item"><a class="nav-link" href="#about">About</a></li>
                        <li class="nav-item"><a class="nav-link" href="#contact">Contact</a></li>
                    </ul>
                </div>
            </div>
        </header>

        <main class="main-content">
            <section id="hero" class="hero-section">
                <div class="container text-center">
                    <h1>Welcome to {name}</h1>
                    <p class="lead">Your dashboard for managing everything efficiently</p>
                    <button class="btn btn-primary btn-lg">Get Started</button>
                </div>
            </section>

            <section id="features" class="features-section py-5">
                <div class="container">
                    <h2 class="text-center mb-5">Features</h2>
                    <div class="row">
                        <div class="col-md-4 mb-4">
                            <div class="card h-100">
                                <div class="card-body text-center">
                                    <i class="fas fa-chart-line fa-3x mb-3 text-primary"></i>
                                    <h5 class="card-title">Analytics</h5>
                                    <p class="card-text">Track and analyze your data with powerful insights.</p>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-4 mb-4">
                            <div class="card h-100">
                                <div class="card-body text-center">
                                    <i class="fas fa-users fa-3x mb-3 text-primary"></i>
                                    <h5 class="card-title">User Management</h5>
                                    <p class="card-text">Manage users and permissions efficiently.</p>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-4 mb-4">
                            <div class="card h-100">
                                <div class="card-body text-center">
                                    <i class="fas fa-cog fa-3x mb-3 text-primary"></i>
                                    <h5 class="card-title">Configuration</h5>
                                    <p class="card-text">Customize settings to fit your needs.</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </section>
        </main>

        <footer class="bg-dark text-white py-4">
            <div class="container text-center">
                <p>&copy; 2024 {name}. All rights reserved.</p>
            </div>
        </footer>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script src="js/{name.lower()}.js"></script>
</body>
</html>'''
        return html_template

    def _generate_css_styles(self, name: str, features: str) -> str:
        css_template = f'''/* {name} Styles */
:root {{
  --primary-color: #007bff;
  --secondary-color: #6c757d;
  --success-color: #28a745;
  --danger-color: #dc3545;
  --warning-color: #ffc107;
  --info-color: #17a2b8;
  --light-color: #f8f9fa;
  --dark-color: #343a40;
}}

* {{
  box-sizing: border-box;
}}

body {{
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  line-height: 1.6;
  color: var(--dark-color);
}}

.{name.lower()}-container {{
  padding: 2rem;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
  margin: 1rem 0;
}}

.hero-section {{
  background: linear-gradient(135deg, var(--primary-color), var(--info-color));
  color: white;
  padding: 5rem 0;
}}

.features-section {{
  background-color: var(--light-color);
}}

.card {{
  transition: transform 0.2s;
  border: none;
  box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
}}

.card:hover {{
  transform: translateY(-5px);
  box-shadow: 0 5px 15px rgba(0, 0, 0, 0.2);
}}

.loading {{
  text-align: center;
  padding: 2rem;
  color: var(--secondary-color);
}}

.btn {{
  border-radius: 25px;
  padding: 0.5rem 2rem;
  font-weight: 500;
  transition: all 0.2s;
}}

.btn:hover {{
  transform: translateY(-2px);
}}

.navbar-brand {{
  font-weight: bold;
  font-size: 1.5rem;
}}

footer {{
  margin-top: auto;
}}

/* Responsive Design */
@media (max-width: 768px) {{
  .hero-section {{
    padding: 3rem 0;
  }}
  
  .hero-section h1 {{
    font-size: 2rem;
  }}
}}'''
        return css_template

    def _generate_js_module(self, name: str, features: str) -> str:
        js_template = f'''// {name} JavaScript Module
class {name}Manager {{
    constructor() {{
        this.data = [];
        this.apiUrl = '/api/{name.lower()}';
        this.init();
    }}

    async init() {{
        try {{
            await this.loadData();
            this.setupEventListeners();
            this.render();
        }} catch (error) {{
            console.error('Initialization error:', error);
        }}
    }}

    async loadData() {{
        try {{
            const response = await fetch(this.apiUrl);
            if (!response.ok) throw new Error('Network response was not ok');
            this.data = await response.json();
        }} catch (error) {{
            console.error('Error loading data:', error);
            this.showError('Failed to load data');
        }}
    }}

    async saveData(item) {{
        try {{
            const response = await fetch(this.apiUrl, {{
                method: 'POST',
                headers: {{
                    'Content-Type': 'application/json',
                }},
                body: JSON.stringify(item)
            }});
            
            if (!response.ok) throw new Error('Save failed');
            return await response.json();
        }} catch (error) {{
            console.error('Error saving data:', error);
            this.showError('Failed to save data');
        }}
    }}

    async deleteItem(id) {{
        try {{
            const response = await fetch(`${{this.apiUrl}}/${{id}}`, {{
                method: 'DELETE'
            }});
            
            if (!response.ok) throw new Error('Delete failed');
            this.data = this.data.filter(item => item.id !== id);
            this.render();
        }} catch (error) {{
            console.error('Error deleting item:', error);
            this.showError('Failed to delete item');
        }}
    }}

    setupEventListeners() {{
        document.addEventListener('DOMContentLoaded', () => {{
            // Add form submission handlers
            const forms = document.querySelectorAll('.{name.lower()}-form');
            forms.forEach(form => {{
                form.addEventListener('submit', this.handleFormSubmit.bind(this));
            }});

            // Add button click handlers
            document.addEventListener('click', (e) => {{
                if (e.target.matches('.delete-btn')) {{
                    const id = e.target.dataset.id;
                    this.deleteItem(id);
                }}
            }});
        }});
    }}

    handleFormSubmit(event) {{
        event.preventDefault();
        const formData = new FormData(event.target);
        const data = Object.fromEntries(formData.entries());
        this.saveData(data);
    }}

    render() {{
        const container = document.querySelector('.{name.lower()}-container');
        if (!container) return;

        container.innerHTML = this.generateHTML();
    }}

    generateHTML() {{
        return `
            <div class="header">
                <h2>{name} Management</h2>
                <button class="btn btn-primary" onclick="this.showAddForm()">Add New</button>
            </div>
            <div class="data-grid">
                ${{this.data.map(item => `
                    <div class="data-item" data-id="${{item.id}}">
                        <h4>${{item.name || 'Unnamed Item'}}</h4>
                        <p>${{item.description || 'No description'}}</p>
                        <div class="actions">
                            <button class="btn btn-sm btn-outline-primary" onclick="this.editItem('${{item.id}}')">Edit</button>
                            <button class="btn btn-sm btn-outline-danger delete-btn" data-id="${{item.id}}">Delete</button>
                        </div>
                    </div>
                `).join('')}}
            </div>
        `;
    }}

    showError(message) {{
        const errorDiv = document.createElement('div');
        errorDiv.className = 'alert alert-danger';
        errorDiv.textContent = message;
        document.body.insertBefore(errorDiv, document.body.firstChild);
        
        setTimeout(() => errorDiv.remove(), 5000);
    }}

    showAddForm() {{
        // Implementation for showing add form modal
        console.log('Show add form');
    }}

    editItem(id) {{
        // Implementation for editing item
        console.log('Edit item:', id);
    }}
}}

// Initialize the manager when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {{
    window.{name.lower()}Manager = new {name}Manager();
}});

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {{
    module.exports = {name}Manager;
}}'''
        return js_template

    def _generate_node_server(self, name: str, features: str) -> str:
        server_template = f'''// {name} Node.js Server
const express = require('express');
const cors = require('cors');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.static('public'));

// In-memory data store (replace with database in production)
let data = [];
let nextId = 1;

// Routes
app.get('/api/{name.lower()}', (req, res) => {{
    res.json(data);
}});

app.get('/api/{name.lower()}/:id', (req, res) => {{
    const id = parseInt(req.params.id);
    const item = data.find(d => d.id === id);
    
    if (!item) {{
        return res.status(404).json({{ error: 'Item not found' }});
    }}
    
    res.json(item);
}});

app.post('/api/{name.lower()}', (req, res) => {{
    const newItem = {{
        id: nextId++,
        ...req.body,
        createdAt: new Date().toISOString()
    }};
    
    data.push(newItem);
    res.status(201).json(newItem);
}});

app.put('/api/{name.lower()}/:id', (req, res) => {{
    const id = parseInt(req.params.id);
    const index = data.findIndex(d => d.id === id);
    
    if (index === -1) {{
        return res.status(404).json({{ error: 'Item not found' }});
    }}
    
    data[index] = {{ ...data[index], ...req.body, updatedAt: new Date().toISOString() }};
    res.json(data[index]);
}});

app.delete('/api/{name.lower()}/:id', (req, res) => {{
    const id = parseInt(req.params.id);
    const index = data.findIndex(d => d.id === id);
    
    if (index === -1) {{
        return res.status(404).json({{ error: 'Item not found' }});
    }}
    
    data.splice(index, 1);
    res.status(204).send();
}});

// Health check
app.get('/health', (req, res) => {{
    res.json({{ status: 'OK', timestamp: new Date().toISOString() }});
}});

// Serve static files
app.get('*', (req, res) => {{
    res.sendFile(path.join(__dirname, 'public', 'index.html'));
}});

// Error handling middleware
app.use((err, req, res, next) => {{
    console.error(err.stack);
    res.status(500).json({{ error: 'Something went wrong!' }});
}});

app.listen(PORT, () => {{
    console.log(`{name} server running on port ${{PORT}}`);
}});

module.exports = app;'''
        return server_template


class ProjectStructureTool(BaseTool):
    """Tool for creating and managing project directory structures"""
    name: str = "ProjectStructure"
    description: str = "Creates project directory structures and manages file organization"

    def _run(self, action: str, project_type: str, project_name: str, features: Optional[str] = None) -> str:
        try:
            if action == "create_structure":
                return self._create_project_structure(project_type, project_name, features)
            elif action == "list_structure":
                return self._list_project_structure(project_name)
            else:
                return "Invalid action. Valid actions: create_structure, list_structure"
        except Exception as e:
            return f"Error managing project structure: {str(e)}"

    def _create_project_structure(self, project_type: str, project_name: str, features: str) -> str:
        """Create a project directory structure based on type"""
        base_path = project_name
        
        if project_type.lower() in ["react", "frontend", "web"]:
            return self._create_react_structure(base_path)
        elif project_type.lower() in ["nodejs", "backend", "api"]:
            return self._create_nodejs_structure(base_path)
        elif project_type.lower() in ["fullstack", "ecommerce"]:
            return self._create_fullstack_structure(base_path)
        else:
            return self._create_generic_structure(base_path)

    def _create_react_structure(self, base_path: str) -> str:
        directories = [
            f"{base_path}/public",
            f"{base_path}/src/components",
            f"{base_path}/src/pages",
            f"{base_path}/src/hooks",
            f"{base_path}/src/services",
            f"{base_path}/src/utils",
            f"{base_path}/src/styles",
            f"{base_path}/src/assets/images",
            f"{base_path}/src/assets/icons"
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
        
        return f"React project structure created at {base_path}"

    def _create_nodejs_structure(self, base_path: str) -> str:
        directories = [
            f"{base_path}/src/controllers",
            f"{base_path}/src/models",
            f"{base_path}/src/routes",
            f"{base_path}/src/middleware",
            f"{base_path}/src/services",
            f"{base_path}/src/utils",
            f"{base_path}/config",
            f"{base_path}/tests",
            f"{base_path}/public"
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
        
        return f"Node.js project structure created at {base_path}"

    def _create_fullstack_structure(self, base_path: str) -> str:
        directories = [
            # Frontend
            f"{base_path}/frontend/public",
            f"{base_path}/frontend/src/components",
            f"{base_path}/frontend/src/pages",
            f"{base_path}/frontend/src/services",
            f"{base_path}/frontend/src/styles",
            f"{base_path}/frontend/src/assets",
            # Backend
            f"{base_path}/backend/src/controllers",
            f"{base_path}/backend/src/models",
            f"{base_path}/backend/src/routes",
            f"{base_path}/backend/src/middleware",
            f"{base_path}/backend/src/services",
            f"{base_path}/backend/config",
            # Shared
            f"{base_path}/shared/types",
            f"{base_path}/shared/utils",
            f"{base_path}/docs",
            f"{base_path}/tests"
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
        
        return f"Full-stack project structure created at {base_path}"

    def _create_generic_structure(self, base_path: str) -> str:
        directories = [
            f"{base_path}/src",
            f"{base_path}/docs",
            f"{base_path}/tests",
            f"{base_path}/config",
            f"{base_path}/assets"
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
        
        return f"Generic project structure created at {base_path}"

    def _list_project_structure(self, project_name: str) -> str:
        """List the structure of an existing project"""
        if not os.path.exists(project_name):
            return f"Project {project_name} does not exist"
        
        structure = []
        for root, dirs, files in os.walk(project_name):
            level = root.replace(project_name, '').count(os.sep)
            indent = ' ' * 2 * level
            structure.append(f"{indent}{os.path.basename(root)}/")
            subindent = ' ' * 2 * (level + 1)
            for file in files:
                structure.append(f"{subindent}{file}")
        
        return "\n".join(structure)


class DatabaseTool(BaseTool):
    """Tool for database operations and schema management"""
    name: str = "Database"
    description: str = "Manages database schemas, migrations, and basic CRUD operations"

    def _run(self, action: str, table_name: str, schema: Optional[str] = None, data: Optional[str] = None) -> str:
        try:
            if action == "create_schema":
                return self._create_database_schema(table_name, schema)
            elif action == "generate_model":
                return self._generate_model_code(table_name, schema)
            elif action == "create_migration":
                return self._create_migration(table_name, schema)
            else:
                return "Invalid action. Valid actions: create_schema, generate_model, create_migration"
        except Exception as e:
            return f"Error with database operation: {str(e)}"

    def _create_database_schema(self, table_name: str, schema: str) -> str:
        """Generate SQL schema for a table"""
        try:
            schema_data = json.loads(schema) if schema else {}
            
            sql_parts = [f"CREATE TABLE {table_name} ("]
            sql_parts.append("    id SERIAL PRIMARY KEY,")
            
            for field, field_type in schema_data.items():
                if field.lower() != 'id':
                    sql_type = self._map_to_sql_type(field_type)
                    sql_parts.append(f"    {field} {sql_type},")
            
            sql_parts.append("    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,")
            sql_parts.append("    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
            sql_parts.append(");")
            
            return "\n".join(sql_parts)
            
        except Exception as e:
            return f"Error creating schema: {str(e)}"

    def _generate_model_code(self, table_name: str, schema: str) -> str:
        """Generate model code for different frameworks"""
        try:
            schema_data = json.loads(schema) if schema else {}
            
            # Generate Mongoose model (Node.js)
            model_code = f"""const mongoose = require('mongoose');

const {table_name.capitalize()}Schema = new mongoose.Schema({{
"""
            
            for field, field_type in schema_data.items():
                if field.lower() != 'id':
                    mongoose_type = self._map_to_mongoose_type(field_type)
                    model_code += f"    {field}: {{{mongoose_type}}},\n"
            
            model_code += """}, {
    timestamps: true
});

module.exports = mongoose.model('""" + table_name.capitalize() + """', """ + table_name.capitalize() + """Schema);"""
            
            return model_code
            
        except Exception as e:
            return f"Error generating model: {str(e)}"

    def _create_migration(self, table_name: str, schema: str) -> str:
        """Create a database migration file"""
        try:
            schema_data = json.loads(schema) if schema else {}
            timestamp = "20240101000000"  # Simple timestamp
            
            migration_code = f"""-- Migration: Create {table_name} table
-- Created: {timestamp}

-- Up
CREATE TABLE {table_name} (
    id SERIAL PRIMARY KEY,
"""
            
            for field, field_type in schema_data.items():
                if field.lower() != 'id':
                    sql_type = self._map_to_sql_type(field_type)
                    migration_code += f"    {field} {sql_type},\n"
            
            migration_code += """    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Down
DROP TABLE IF EXISTS """ + table_name + """;"""
            
            return migration_code
            
        except Exception as e:
            return f"Error creating migration: {str(e)}"

    def _map_to_sql_type(self, field_type: str) -> str:
        """Map generic types to SQL types"""
        type_mapping = {
            "string": "VARCHAR(255)",
            "text": "TEXT",
            "integer": "INTEGER",
            "float": "DECIMAL(10,2)",
            "boolean": "BOOLEAN",
            "date": "DATE",
            "datetime": "TIMESTAMP",
            "email": "VARCHAR(255)",
            "url": "VARCHAR(500)"
        }
        return type_mapping.get(field_type.lower(), "VARCHAR(255)")

    def _map_to_mongoose_type(self, field_type: str) -> str:
        """Map generic types to Mongoose types"""
        type_mapping = {
            "string": "type: String, required: true",
            "text": "type: String",
            "integer": "type: Number, required: true",
            "float": "type: Number",
            "boolean": "type: Boolean, default: false",
            "date": "type: Date",
            "datetime": "type: Date, default: Date.now",
            "email": "type: String, lowercase: true, trim: true",
            "url": "type: String"
        }
        return type_mapping.get(field_type.lower(), "type: String")