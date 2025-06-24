from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, flash
from werkzeug.utils import secure_filename
import os
import tempfile
import shutil
import zipfile
from datetime import datetime
from openrouter_client import OpenRouterClient
from generate_files import FileGenerator

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Change this to a secure secret key

# Configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
OUTPUT_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'generated_projects')
ALLOWED_EXTENSIONS = {'zip'}

# Ensure directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Available models with descriptions
MODELS = [
    {"id": "openai/gpt-4", "name": "GPT-4 (Most Capable)"},
    {"id": "mistralai/mixtral-8x7b-instruct", "name": "Mixtral (Fast & Free)"},
    {"id": "google/gemini-pro", "name": "Gemini Pro (Good Balance)"},
    {"id": "anthropic/claude-2", "name": "Claude 2 (Helpful & Detailed)"}
]

# Common backend project templates
BACKEND_TEMPLATES = [
    {
        "id": "rest-api",
        "name": "REST API",
        "description": "A basic RESTful API with Flask/FastAPI",
        "prompt": "Create a RESTful API with endpoints for a simple task manager. Include CRUD operations for tasks with fields: id, title, description, completed, created_at. Use Flask or FastAPI with SQLAlchemy for the database. Include proper error handling and input validation."
    },
    {
        "id": "auth-system",
        "name": "Authentication System",
        "description": "User registration, login, and JWT authentication",
        "prompt": "Create a complete authentication system with user registration, login, and JWT token generation. Include password hashing, email verification, and password reset functionality. Use Flask/Python with SQLAlchemy and PyJWT."
    },
    {
        "id": "file-upload",
        "name": "File Upload Service",
        "description": "Handle file uploads with validation and storage",
        "prompt": "Create a file upload service that accepts various file types, validates them, and stores them securely. Include features like file size limits, MIME type checking, and generating secure download links. Use Python with Flask and store files in a configurable location (local filesystem or cloud storage)."
    },
    {
        "id": "websocket-chat",
        "name": "WebSocket Chat",
        "description": "Real-time chat application using WebSockets",
        "prompt": "Create a real-time chat application using WebSockets. Include features like multiple chat rooms, user nicknames, and message history. Use Flask-SocketIO for the WebSocket implementation and include a simple HTML/JS frontend to test the functionality."
    }
]

# Educational resources
RESOURCES = [
    {"title": "Flask Documentation", "url": "https://flask.palletsprojects.com/", "category": "Framework"},
    {"title": "SQLAlchemy ORM Guide", "url": "https://docs.sqlalchemy.org/en/20/orm/", "category": "Database"},
    {"title": "REST API Best Practices", "url": "https://www.freecodecamp.org/news/rest-api-best-practices/", "category": "API Design"},
    {"title": "Web Security Fundamentals", "url": "https://owasp.org/www-project-top-ten/", "category": "Security"}
]

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def create_zip(source_folder, output_filename):
    """Create a zip file from a folder"""
    with zipfile.ZipFile(output_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(source_folder):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, source_folder)
                zipf.write(file_path, arcname)

def generate_code(prompt, model, api_key):
    """Helper function to generate code using the specified model"""
    try:
        # Initialize the OpenRouter client
        client = OpenRouterClient(api_key=api_key)
        
        # Add system message to guide the AI
        system_message = """You are a helpful coding assistant that helps students learn backend development. 
        Generate clean, well-documented code with comments explaining key concepts. 
        Follow best practices for the specified technology stack."""
        
        # Call the AI model
        response = client.generate_code(
            prompt=prompt,
            model=model,
            system_message=system_message
        )
        
        return response
    except Exception as e:
        app.logger.error(f"Error generating code: {str(e)}")
        raise

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Get form data
        prompt = request.form.get('prompt', '').strip()
        model = request.form.get('model', MODELS[0]['id'])
        api_key = request.form.get('api_key', '').strip()
        template_id = request.form.get('template', '')
        
        # If a template was selected, use its prompt
        if template_id and template_id != 'custom':
            template = next((t for t in BACKEND_TEMPLATES if t['id'] == template_id), None)
            if template:
                prompt = template['prompt']
                
        # If no prompt and no template, show error
        if not prompt:
            flash('Please enter a prompt or select a template', 'error')
            return render_template('index.html', 
                                models=MODELS, 
                                default_model=model,
                                templates=BACKEND_TEMPLATES,
                                resources=RESOURCES)
        
        # Check for required fields
        if not prompt:
            flash('Please enter a prompt', 'error')
            return redirect(url_for('index'))
        
        if not api_key:
            flash('Please enter your OpenRouter API key', 'error')
            return redirect(url_for('index'))
        
        # Create a temporary directory for the project
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        project_dir = os.path.join(OUTPUT_FOLDER, f'project_{timestamp}')
        os.makedirs(project_dir, exist_ok=True)
        
        try:
            # Initialize client and generate files
            client = OpenRouterClient(api_key)
            file_generator = FileGenerator()
            
            # Generate files
            generated_files = file_generator.generate_from_prompt(
                prompt=prompt,
                output_dir=project_dir,
                client=client
            )
            
            if not generated_files:
                flash('No files were generated', 'error')
                return redirect(url_for('index'))
            
            # Create a zip file of the project
            zip_filename = os.path.join(OUTPUT_FOLDER, f'project_{timestamp}.zip')
            create_zip(project_dir, zip_filename)
            
            # Store the zip filename in the session
            session['download_file'] = os.path.basename(zip_filename)
            
            # Get the first file's content for preview
            preview_file = generated_files[0]
            with open(preview_file, 'r', encoding='utf-8') as f:
                preview_content = f.read()
            
            return render_template('result.html', 
                                 preview_content=preview_content,
                                 preview_filename=os.path.basename(preview_file),
                                 file_count=len(generated_files))
            
        except Exception as e:
            flash(f'Error generating code: {str(e)}', 'error')
            return redirect(url_for('index'))
    
    # GET request - show the form
    return render_template('index.html', models=MODELS, default_model=MODELS[0])

@app.route('/download')
def download():
    """Download the generated project zip file"""
    if 'download_file' not in session:
        flash('No file to download', 'error')
        return redirect(url_for('index'))
    
    zip_filename = os.path.join(OUTPUT_FOLDER, session['download_file'])
    
    if not os.path.exists(zip_filename):
        flash('File not found', 'error')
        return redirect(url_for('index'))
    
    return send_file(
        zip_filename,
        as_attachment=True,
        download_name=f"generated_project_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
    )

@app.route('/preview/<path:filename>')
def preview_file(filename):
    """Preview a specific file from the generated project"""
    if 'download_file' not in session:
        return "No project available", 404
    
    # Get the project directory from the zip filename
    project_zip = os.path.join(OUTPUT_FOLDER, session['download_file'])
    project_dir = os.path.splitext(project_zip)[0]
    
    # Build the full path to the requested file
    filepath = os.path.join(project_dir, filename)
    
    # Check if the file exists and is within the project directory
    if not os.path.exists(filepath) or not os.path.abspath(filepath).startswith(os.path.abspath(project_dir)):
        return "File not found", 404
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return render_template('preview.html', 
                             filename=filename, 
                             content=content,
                             file_count=0)  # We don't have the file count here
    except UnicodeDecodeError:
        return "Cannot preview binary file", 400

# Create templates directory if it doesn't exist
templates_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
os.makedirs(templates_dir, exist_ok=True)

# Create base template
base_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}AI Code Generator{% endblock %}</title>
    <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.7.0/styles/atom-one-dark.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.7.0/highlight.min.js"></script>
    <script>hljs.highlightAll();</script>
    <style>
        .code-block {
            font-family: 'Fira Code', 'Courier New', monospace;
            font-size: 0.9em;
            line-height: 1.5;
        }
        .file-tree {
            max-height: 400px;
            overflow-y: auto;
        }
    </style>
</head>
<body class="bg-gray-100">
    <nav class="bg-blue-600 text-white p-4">
        <div class="container mx-auto flex justify-between items-center">
            <h1 class="text-2xl font-bold">AI Code Generator</h1>
            <a href="{{ url_for('index') }}" class="hover:underline">New Project</a>
        </div>
    </nav>

    <main class="container mx-auto p-4">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="mb-4 p-4 rounded-md {% if category == 'error' %}bg-red-100 text-red-700{% else %}bg-green-100 text-green-700{% endif %}">
                        {{ message }}
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        {% block content %}{% endblock %}
    </main>

    <footer class="mt-8 py-4 bg-gray-800 text-white">
        <div class="container mx-auto text-center">
            <p>AI Code Generator &copy; {{ now.year }}</p>
        </div>
    </footer>
</body>
</html>
"""

# Create index template
index_template = """
{% extends "base.html" %}

{% block title %}Generate Code - AI Code Generator{% endblock %}

{% block content %}
<div class="max-w-4xl mx-auto bg-white rounded-lg shadow-md p-6">
    <h2 class="text-2xl font-bold mb-6">Generate Code with AI</h2>
    
    <form method="POST" action="{{ url_for('index') }}" class="space-y-6">
        <div>
            <label for="api_key" class="block text-sm font-medium text-gray-700 mb-1">OpenRouter API Key</label>
            <input type="password" id="api_key" name="api_key" 
                   class="w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                   placeholder="Enter your OpenRouter API key" required>
            <p class="mt-1 text-sm text-gray-500">
                Get your API key from <a href="https://openrouter.ai/keys" target="_blank" class="text-blue-600 hover:underline">OpenRouter</a>
            </p>
        </div>
        
        <div>
            <label for="model" class="block text-sm font-medium text-gray-700 mb-1">Model</label>
            <select id="model" name="model" 
                    class="w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500">
                {% for model in models %}
                    <option value="{{ model }}" {% if model == default_model %}selected{% endif %}>{{ model }}</option>
                {% endfor %}
            </select>
        </div>
        
        <div>
            <label for="prompt" class="block text-sm font-medium text-gray-700 mb-1">Prompt</label>
            <textarea id="prompt" name="prompt" rows="6" 
                      class="w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="Describe the code you want to generate..." required></textarea>
            <p class="mt-1 text-sm text-gray-500">
                Be as specific as possible about the functionality, programming language, and any requirements.
            </p>
        </div>
        
        <div class="grid grid-cols-1 gap-4 mt-6">
            <div>
                <label for="template" class="block text-sm font-medium text-gray-700 mb-1">Project Template (Optional)</label>
                <select id="template" name="template" 
                        class="w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500">
                    <option value="custom">Custom (Write your own prompt)</option>
                    {% for template in templates %}
                        <option value="{{ template.id }}">{{ template.name }} - {{ template.description }}</option>
                    {% endfor %}
                </select>
            </div>
            
            <div class="pt-2">
                <button type="submit" 
                        class="w-full px-6 py-3 bg-blue-600 text-white font-medium rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 text-lg">
                    🚀 Generate Code
                </button>
            </div>
        </div>
        
        <div class="mt-8 pt-6 border-t border-gray-200">
            <h3 class="text-lg font-medium text-gray-900 mb-4">Learning Resources</h3>
            <div class="grid md:grid-cols-2 gap-4">
                {% for resource in resources %}
                <a href="{{ resource.url }}" target="_blank" 
                   class="p-4 bg-gray-50 rounded-md hover:bg-blue-50 transition-colors">
                    <p class="font-medium text-blue-600">{{ resource.title }}</p>
                    <p class="text-sm text-gray-500">{{ resource.category }}</p>
                </a>
                {% endfor %}
            </div>
        </div>
    </form>
    
    <div class="mt-8 pt-6 border-t border-gray-200">
        <h3 class="text-lg font-medium text-gray-900 mb-4">Examples</h3>
        <div class="grid md:grid-cols-2 gap-4">
            <div class="p-4 bg-gray-50 rounded-md">
                <p class="font-medium mb-2">Simple Web App</p>
                <p class="text-sm text-gray-600">"Create a Flask web app with a form that takes a name and displays a greeting. Include HTML templates and CSS styling."</p>
            </div>
            <div class="p-4 bg-gray-50 rounded-md">
                <p class="font-medium mb-2">Data Analysis</p>
                <p class="text-sm text-gray-600">"Generate a Python script using pandas to load a CSV file, clean the data, and create a bar plot with matplotlib."</p>
            </div>
        </div>
    </div>
</div>
{% endblock %}
"""

# Create result template
result_template = """
{% extends "base.html" %}

{% block title %}Generated Code - AI Code Generator{% endblock %}

{% block content %}
<div class="max-w-6xl mx-auto bg-white rounded-lg shadow-md overflow-hidden">
    <div class="p-6">
        <div class="flex justify-between items-center mb-6">
            <h2 class="text-2xl font-bold">Generated Code</h2>
            <div class="space-x-2">
                <a href="{{ url_for('download') }}" 
                   class="px-4 py-2 bg-blue-600 text-white font-medium rounded-md hover:bg-blue-700">
                    Download Project (ZIP)
                </a>
                <a href="{{ url_for('index') }}" 
                   class="px-4 py-2 border border-gray-300 font-medium rounded-md hover:bg-gray-50">
                    New Project
                </a>
            </div>
        </div>
        
        <div class="mb-4">
            <p class="text-sm text-gray-600">
                Successfully generated <span class="font-medium">{{ file_count }} files</span>.
                Previewing: <span class="font-mono text-sm bg-gray-100 px-2 py-1 rounded">{{ preview_filename }}</span>
            </p>
        </div>
    </div>
    
    <div class="border-t border-gray-200">
        <div class="flex">
            <div class="w-1/4 border-r border-gray-200 bg-gray-50 file-tree p-4 overflow-y-auto">
                <div class="flex justify-between items-center mb-3">
                    <h3 class="font-medium text-gray-900">Project Files</h3>
                    <button id="explain-code" class="text-xs text-blue-600 hover:underline">Explain Code</button>
                </div>
                <div id="file-tree" class="space-y-1">
                    <!-- Files will be populated by JavaScript -->
                </div>
                
                <!-- Code Explanation Panel (initially hidden) -->
                <div id="explanation-panel" class="mt-6 p-4 bg-yellow-50 border border-yellow-200 rounded-md hidden">
                    <h4 class="font-medium text-yellow-800 mb-2">Code Explanation</h4>
                    <div id="code-explanation" class="text-sm text-gray-700">
                        Loading explanation...
                    </div>
                </div>
            </div>
            
            <div class="w-3/4">
                <div class="p-0 overflow-hidden">
                    <pre class="m-0"><code class="language-python code-block">{{ preview_content|e }}</code></pre>
                </div>
            </div>
        </div>
    </div>
    
    <div class="p-4 bg-gray-50 border-t border-gray-200 text-sm text-gray-600">
        <p>Tip: Review the generated code before using it in production. Make sure to test thoroughly.</p>
    </div>
</div>
{% endblock %}
"""

# Create preview template
preview_template = """
{% extends "base.html" %}

{% block title %}{{ filename }} - Preview{% endblock %}

{% block content %}
<div class="max-w-6xl mx-auto bg-white rounded-lg shadow-md overflow-hidden">
    <div class="p-4 border-b border-gray-200 bg-gray-50">
        <div class="flex justify-between items-center">
            <h2 class="text-lg font-medium text-gray-900">{{ filename }}</h2>
            <a href="{{ url_for('download') }}" 
               class="px-3 py-1 text-sm bg-blue-600 text-white font-medium rounded-md hover:bg-blue-700">
                Download Project
            </a>
        </div>
    </div>
    
    <div class="p-0 overflow-hidden">
        <pre class="m-0"><code class="language-{{ file_extension }}">{{ content|e }}</code></pre>
    </div>
    
    <script>
    // Apply syntax highlighting
    hljs.highlightAll();
    
    // File tree navigation
    document.addEventListener('DOMContentLoaded', function() {
        // This would be populated from the server in a real implementation
        const files = [
            { name: 'app.py', path: 'app.py', type: 'file' },
            { name: 'requirements.txt', path: 'requirements.txt', type: 'file' },
            { 
                name: 'templates', 
                type: 'directory',
                children: [
                    { name: 'index.html', path: 'templates/index.html', type: 'file' },
                    { name: 'base.html', path: 'templates/base.html', type: 'file' }
                ]
            },
            { name: 'static', type: 'directory', children: [] },
            { name: 'models.py', path: 'models.py', type: 'file' },
            { name: 'config.py', path: 'config.py', type: 'file' }
        ];
        
        // Render file tree
        function renderFileTree(items, container) {
            container.innerHTML = '';
            items.forEach(item => {
                const element = document.createElement('div');
                element.className = 'pl-2';
                
                if (item.type === 'directory') {
                    element.innerHTML = `
                        <div class="flex items-center py-1 cursor-pointer hover:bg-gray-100 rounded">
                            <span class="mr-1">📁</span>
                            <span class="text-sm">${item.name}</span>
                        </div>
                    `;
                    
                    if (item.children && item.children.length > 0) {
                        const childContainer = document.createElement('div');
                        childContainer.className = 'pl-4 hidden';
                        element.appendChild(childContainer);
                        
                        element.querySelector('div').addEventListener('click', () => {
                            childContainer.classList.toggle('hidden');
                        });
                        
                        renderFileTree(item.children, childContainer);
                    }
                } else {
                    element.innerHTML = `
                        <a href="#" data-file="${item.path}" class="flex items-center py-1 text-blue-600 hover:underline">
                            <span class="mr-1 text-xs">📄</span>
                            <span class="text-sm">${item.name}</span>
                        </a>
                    `;
                }
                
                container.appendChild(element);
            });
        }
        
        // Initialize file tree
        const fileTreeContainer = document.getElementById('file-tree');
        renderFileTree(files, fileTreeContainer);
        
        // Handle file clicks
        fileTreeContainer.addEventListener('click', (e) => {
            const fileLink = e.target.closest('a[data-file]');
            if (fileLink) {
                e.preventDefault();
                const fileName = fileLink.getAttribute('data-file');
                // In a real implementation, this would load the file content via AJAX
                console.log('Selected file:', fileName);
            }
        });
        
        // Handle explain code button
        document.getElementById('explain-code').addEventListener('click', async () => {
            const explanationPanel = document.getElementById('explanation-panel');
            const explanationContent = document.getElementById('code-explanation');
            
            explanationPanel.classList.remove('hidden');
            explanationContent.textContent = 'Analyzing code and generating explanation...';
            
            try {
                // In a real implementation, this would call the backend to generate an explanation
                // For now, we'll simulate a response
                await new Promise(resolve => setTimeout(resolve, 1000));
                
                explanationContent.innerHTML = `
                    <p class="mb-2">This code implements a RESTful API endpoint for managing tasks. Here's what it does:</p>
                    <ul class="list-disc pl-5 space-y-1">
                        <li>Defines a route for <code class="bg-gray-100 px-1 rounded">/api/tasks</code> that handles GET and POST requests</li>
                        <li>Uses Flask's <code class="bg-gray-100 px-1 rounded">request</code> object to handle JSON data</li>
                        <li>Implements basic error handling with try/except blocks</li>
                        <li>Returns appropriate HTTP status codes (200, 201, 400, 500)</li>
                    </ul>
                    <p class="mt-2 text-sm text-gray-600">This is a basic implementation. In a production environment, you'd want to add authentication, input validation, and database persistence.</p>
                `;
            } catch (error) {
                explanationContent.textContent = 'Failed to generate explanation. Please try again.';
                console.error('Error generating explanation:', error);
            }
        });
    });
    </script>
{% endblock %}
"""

# Write template files
with open(os.path.join(templates_dir, 'base.html'), 'w', encoding='utf-8') as f:
    f.write(base_template)

with open(os.path.join(templates_dir, 'index.html'), 'w', encoding='utf-8') as f:
    f.write(index_template)


with open(os.path.join(templates_dir, 'result.html'), 'w', encoding='utf-8') as f:
    f.write(result_template)


with open(os.path.join(templates_dir, 'preview.html'), 'w', encoding='utf-8') as f:
    f.write(preview_template)

# Add current year to the context
@app.context_processor
def inject_now():
    return {'now': datetime.now()}

if __name__ == '__main__':
    app.run(debug=True)
