import os

def find_csrf_exempt(directory):
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                path = os.path.join(root, file)
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if 'csrf_exempt' in content:
                        print(f'Found CSRF_EXEMPT in {path}')
                    if 'method_decorator' in content:
                        print(f'Found method_decorator in {path}')

find_csrf_exempt('d:\\devsec-demo\\Munyabugingo')
