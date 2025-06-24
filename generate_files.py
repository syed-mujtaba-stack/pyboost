import os
import re
import json
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum

class TemplateType(str, Enum):
    PYTHON = "python"
    WEB = "web"
    DATA_SCIENCE = "data_science"
    FLASK = "flask"
    DJANGO = "django"
    FASTAPI = "fastapi"
    REACT = "react"
    VUE = "vue"
    DEFAULT = "default"

@dataclass
class FileTemplate:
    path: str
    content: str = ""
    is_directory: bool = False
    children: List['FileTemplate'] = field(default_factory=list)

class FileGenerator:
    TEMPLATES = {
        TemplateType.PYTHON: [
            FileTemplate("requirements.txt", "# Python dependencies\n"),
            FileTemplate("README.md", "# Python Project\n\nA new Python project."),
            FileTemplate("src", is_directory=True, children=[
                FileTemplate("__init__.py"),
                FileTemplate("main.py", "def main():\n    print(\"Hello, World!\")\n\nif __name__ == \"__main__\":\n    main()")
            ])
        ],
        TemplateType.WEB: [
            FileTemplate("index.html", "<!DOCTYPE html>\n<html>\n<head>\n    <title>Web Project</title>\n    <link rel=\"stylesheet\" href=\"styles.css\">\n</head>\n<body>\n    <h1>Welcome to My Web Project</h1>\n    <script src=\"app.js\"></script>\n</body>\n</html>"),
            FileTemplate("styles.css", "body { font-family: Arial, sans-serif; margin: 0; padding: 20px; }"),
            FileTemplate("app.js", "// Your JavaScript code here\nconsole.log('Hello, Web!');")
        ],
        # Add more templates as needed
    }
    
    @classmethod
    def get_available_templates(cls) -> List[str]:
        """Get list of available template names"""
        return [t.value for t in TemplateType]
    
    @classmethod
    def get_template(cls, template_type: Union[str, TemplateType]) -> List[FileTemplate]:
        """Get files for a specific template"""
        if isinstance(template_type, str):
            try:
                template_type = TemplateType(template_type.lower())
            except ValueError:
                template_type = TemplateType.DEFAULT
        
        return cls.TEMPLATES.get(template_type, [])
    
    @classmethod
    def create_directory(cls, path: Union[str, Path]) -> None:
        """Create directory if it doesn't exist"""
        Path(path).mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def extract_code_blocks(cls, content: str) -> Dict[str, str]:
        """
        Extract code blocks from markdown content
        
        Args:
            content: Markdown content with code blocks
            
        Returns:
            Dict where keys are filenames and values are file contents
        """
        pattern = r'```(?:[a-zA-Z0-9_]*\n)?([\s\S]*?)```'
        code_blocks = re.findall(pattern, content)
        
        files = {}
        for i, block in enumerate(code_blocks, 1):
            # Try to extract filename from the first line of the block
            lines = block.strip().split('\n')
            first_line = lines[0].strip()
            
            if ':' in first_line and '\n' in block:
                # If first line looks like a filename (contains : and there are more lines)
                filename = first_line.split(':', 1)[0].strip()
                content = '\n'.join(lines[1:]).lstrip('\n')
                files[filename] = content
            else:
                # Default filename if no filename detected
                files[f'file_{i}.py'] = block
                
        return files
    
    @classmethod
    def write_files(
        cls, 
        files: Dict[str, str], 
        output_dir: Union[str, Path] = '.',
        overwrite: bool = False,
        skip_existing: bool = False
    ) -> List[str]:
        """
        Write files to the specified directory
        
        Args:
            files: Dictionary of {filename: content}
            output_dir: Directory to write files to
            overwrite: Whether to overwrite existing files
            skip_existing: Whether to skip existing files
            
        Returns:
            List of created/updated file paths
        """
        output_dir = Path(output_dir)
        created_files = []
        
        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)
        
        for filename, content in files.items():
            filepath = output_dir / filename
            
            # Skip if file exists and we're not overwriting
            if filepath.exists() and not overwrite:
                if skip_existing:
                    continue
                else:
                    raise FileExistsError(f"File already exists: {filepath}")
            
            # Ensure parent directory exists
            filepath.parent.mkdir(parents=True, exist_ok=True)
            
            # Write file content
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
                
            created_files.append(str(filepath.absolute()))
            
        return created_files
        
    @classmethod
    def create_from_template(
        cls,
        template_type: Union[str, TemplateType],
        output_dir: Union[str, Path],
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> List[str]:
        """
        Create files from a template
        
        Args:
            template_type: Type of template to use
            output_dir: Directory to create files in
            context: Variables to use for template rendering
            **kwargs: Additional arguments for write_files
            
        Returns:
            List of created file paths
        """
        if context is None:
            context = {}
            
        templates = cls.get_template(template_type)
        created_files = []
        
        def process_template(template: FileTemplate, base_path: Path):
            current_path = base_path / template.path
            
            if template.is_directory:
                current_path.mkdir(exist_ok=True)
                for child in template.children:
                    process_template(child, current_path)
            else:
                # Simple template rendering (could be extended with a real template engine)
                content = template.content
                for key, value in context.items():
                    content = content.replace(f'{{{{ {key} }}}}', str(value))
                
                current_path.parent.mkdir(parents=True, exist_ok=True)
                with open(current_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                created_files.append(str(current_path.absolute()))
        
        for template in templates:
            process_template(template, Path(output_dir))
            
        return created_files
    
    @classmethod
    def generate_from_prompt(
        cls, 
        prompt: str, 
        output_dir: Union[str, Path] = '.', 
        client=None,
        template: Optional[Union[str, TemplateType]] = None,
        context: Optional[Dict[str, Any]] = None,
        **generation_kwargs
    ) -> Dict[str, Any]:
        """
        Generate files from a prompt using the provided client
        
        Args:
            prompt: The prompt to generate code from
            output_dir: Directory to write files to
            client: OpenRouterClient instance
            template: Optional template to use
            context: Additional context for template rendering
            **generation_kwargs: Additional arguments for generate_code
            
        Returns:
            Dict containing:
                - files: List of created file paths
                - metadata: Generation metadata
                - raw_response: Raw response from the API
        """
        if client is None:
            from openrouter_client import OpenRouterClient
            client = OpenRouterClient()
        
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create a more detailed system prompt
        system_prompt = """You are an expert AI coding assistant that generates complete, production-ready code.
        
        Instructions:
        1. Generate complete, runnable code
        2. Include all necessary imports and dependencies
        3. Follow best practices for the language/framework
        4. Add appropriate error handling and documentation
        5. Format your response with each file in a code block
        
        Format each file like this:
        
        filename.py:
        ```python
        # Code here
        ```
        
        For directories, use forward slashes (e.g., 'src/utils/helpers.py')
        """
        
        # Add template context to prompt if provided
        if template:
            template_info = f"\n\nUse the {template} template as a starting point."
            if context:
                template_info += f" Context: {json.dumps(context, indent=2)}"
            prompt = template_info + "\n\n" + prompt
        
        # Generate code
        response = client.generate_code(
            prompt=prompt,
            system_prompt=system_prompt,
            **generation_kwargs
        )
        
        # Extract and write files
        files = cls.extract_code_blocks(response)
        
        # Create from template first if specified
        if template:
            try:
                template_files = cls.create_from_template(
                    template_type=template,
                    output_dir=output_dir,
                    context=context,
                    overwrite=False,
                    skip_existing=True
                )
            except Exception as e:
                print(f"Warning: Failed to create from template: {e}")
        
        # Write generated files
        try:
            created_files = cls.write_files(
                files=files,
                output_dir=output_dir,
                overwrite=True
            )
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "files": [],
                "metadata": {"template": str(template) if template else None},
                "raw_response": response
            }
        
        return {
            "success": True,
            "files": created_files,
            "metadata": {
                "template": str(template) if template else None,
                "file_count": len(created_files),
                "generation_params": generation_kwargs
            },
            "raw_response": response
        }

if __name__ == "__main__":
    # Example usage
    import sys
    from openrouter_client import OpenRouterClient
    
    if len(sys.argv) < 2:
        print("Usage: python generate_files.py <prompt> [output_dir]")
        sys.exit(1)
        
    prompt = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else '.'
    
    client = OpenRouterClient()
    created_files = FileGenerator.generate_from_prompt(prompt, output_dir, client)
    
    print(f"Created {len(created_files)} files:")
    for file in created_files:
        print(f"- {file}")
