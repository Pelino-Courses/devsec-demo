import os

def find_csrf_exempt(directory):
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                path = os.path.join(root, file)
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        for i, line in enumerate(lines):
                            if 'csrf_exempt' in line:
                                print(f'Found CSRF_EXEMPT in {path} at line {i+1}')
                            if 'method_decorator' in line:
                                print(f'Found method_decorator in {path} at line {i+1}')
                except:
                    pass

find_csrf_exempt('.')
