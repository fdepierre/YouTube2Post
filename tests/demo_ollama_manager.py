#!/usr/bin/env python3

import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../modules')))

from ollama_manager import OllamaManager

def format_size(size_bytes):
    """Format size in bytes to human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.2f} TB"

def main():
    # Initialize with any model name, it doesn't matter for listing
    ollama = OllamaManager('llama2')
    
    print("\n=== Available Models ===")
    try:
        models = ollama.list_available_models()
        if not models:
            print("No models found")
        else:
            # Handle both list and dict responses
            model_list = models if isinstance(models, list) else models.get('models', [])
            for model in model_list:
                # Handle tuple or dict model info
                if isinstance(model, tuple):
                    model_name = model[0]
                    model_info = model[1]
                    print(f"Model: {model_name}")
                    if hasattr(model_info, 'size'):
                        print(f"  Size: {format_size(model_info.size)}")
                    if hasattr(model_info, 'modified_at'):
                        print(f"  Modified: {model_info.modified_at}")
                    if hasattr(model_info, 'details'):
                        details = model_info.details
                        if hasattr(details, 'parameter_size'):
                            print(f"  Parameters: {details.parameter_size}")
                        if hasattr(details, 'quantization_level'):
                            print(f"  Quantization: {details.quantization_level}")
                        if hasattr(details, 'family'):
                            print(f"  Family: {details.family}")
                else:
                    # Handle dict format
                    print(f"Model: {model.get('name', 'Unknown')}")
                    if 'size' in model:
                        print(f"  Size: {format_size(model['size'])}")
                    if 'modified_at' in model:
                        print(f"  Modified: {model['modified_at']}")
                    if 'details' in model:
                        details = model['details']
                        if details.get('parameter_size'):
                            print(f"  Parameters: {details['parameter_size']}")
                        if details.get('quantization_level'):
                            print(f"  Quantization: {details['quantization_level']}")
                        if details.get('family'):
                            print(f"  Family: {details['family']}")
                print()
    except Exception as e:
        print(f"Error listing available models: {e}")

    print("\n=== Running Models ===")
    try:
        running = ollama.list_running_models()
        if not running:
            print("No models currently running")
        else:
            for model in running:
                if isinstance(model, dict):
                    print(f"Model: {model.get('model', 'Unknown')}")
                    if 'total_gpu_memory' in model:
                        print(f"  Total GPU Memory: {format_size(model['total_gpu_memory'])}")
                    if 'gpu_memory_usage' in model:
                        print(f"  GPU Memory Usage: {format_size(model['gpu_memory_usage'])}")
                else:
                    print(f"Model: {model}")
                print()
    except Exception as e:
        print(f"Error listing running models: {e}")

if __name__ == '__main__':
    main()
