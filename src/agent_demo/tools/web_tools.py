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