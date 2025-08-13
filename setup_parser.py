import os
import subprocess
import sys
from tree_sitter import Language
import shutil
import stat

GRAMMARS = {
    'c_sharp': {
        'repo': 'https://github.com/tree-sitter/tree-sitter-c-sharp',
        'path': [''],
    }
}


BASE_DIR = os.path.dirname(__file__)
BUILD_DIR = os.path.join(BASE_DIR, 'build')
TMP_GRAMMAR_DIR = os.path.join(BASE_DIR, 'tmp_grammars')
EXT = '.dll' if os.name == 'nt' else '.so'
LANG_SO_PATH = os.path.join(BUILD_DIR, f'my-languages{EXT}')

def run_command(command, cwd=None):
    print(f">>> Run: {command}")
    try:
        subprocess.run(command, cwd=cwd, check=True, shell=True)
    except subprocess.CalledProcessError as e:
        print(f"Error when running: {command}")
        sys.exit(1)

def check_requirements():
    try:
        subprocess.run(["tree-sitter", "--version"], stdout=subprocess.DEVNULL, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        print("Missing `tree-sitter-cli`. Install by: npm install -g tree-sitter-cli")
        sys.exit(1)

    try:
        subprocess.run(["git", "--version"], stdout=subprocess.DEVNULL, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        print("Missing `git`. Please install git.")
        sys.exit(1)

def ensure_js_grammar_link(grammar_dir, js_repo_dir):
    node_modules_dir = os.path.join(grammar_dir, "node_modules")
    target = os.path.join(node_modules_dir, "tree-sitter-javascript")
    if not os.path.exists(node_modules_dir):
        os.makedirs(node_modules_dir)
    if not os.path.exists(target):
        shutil.copytree(js_repo_dir, target)

def clone_and_generate():
    lang_paths = []

    os.makedirs(TMP_GRAMMAR_DIR, exist_ok=True)

    for name, conf in GRAMMARS.items():
        print(f"\nPrepare grammar for: {name}")
        repo_url = conf['repo']
        repo_name = os.path.basename(repo_url)
        repo_dir = os.path.join(TMP_GRAMMAR_DIR, repo_name)

        if not os.path.exists(repo_dir):
            print(f"Clone repo: {repo_url}")
            run_command(f"git clone {repo_url} {repo_dir}")
        else:
            print(f"Already have repo: {repo_name}")

        if name == "typescript":
            run_command("npm install", cwd=repo_dir)
            run_command("npm install tree-sitter-javascript", cwd=repo_dir)
            js_repo_dir = os.path.join(TMP_GRAMMAR_DIR, "tree-sitter-javascript")

        if name == "angular":
            run_command("npm install", cwd=repo_dir)
            run_command("npm install tree-sitter-html", cwd=repo_dir)
            js_repo_dir = os.path.join(TMP_GRAMMAR_DIR, "tree-sitter-html")

        for path in conf['path']:
            grammar_dir = os.path.join(repo_dir, path)
            print(f"Generate parser in: {grammar_dir}")
            if name == "typescript":
                ensure_js_grammar_link(grammar_dir, js_repo_dir)
            run_command("tree-sitter generate", cwd=grammar_dir)
            lang_paths.append(grammar_dir)

    return lang_paths

def build_library(lang_dirs):
    print(f"\n Build parser → {LANG_SO_PATH}")
    os.makedirs(BUILD_DIR, exist_ok=True)
    Language.build_library(LANG_SO_PATH, lang_dirs)
    print(f"Build done: {LANG_SO_PATH}")

def remove_readonly(func, path, excinfo):
    import os
    os.chmod(path, stat.S_IWRITE)
    func(path)

def main():
    if os.path.exists(LANG_SO_PATH):
        print(f"Already have parser: {LANG_SO_PATH}")
        return

    lang_dirs = clone_and_generate()
    build_library(lang_dirs)

    if os.path.exists(TMP_GRAMMAR_DIR):
        print(f"Remove tmp grammar dir: {TMP_GRAMMAR_DIR}")
        shutil.rmtree(TMP_GRAMMAR_DIR, onerror=remove_readonly)

if __name__ == "__main__":
    main()
