import yaml
import os
import sys

DEFAULT_CONFIG_PATH = 'config.yaml'

def load_config(config_path: str = DEFAULT_CONFIG_PATH) -> dict:
    """Tải cấu hình từ file YAML."""
    print(f"Loading configuration from: {config_path}")
    if not os.path.exists(config_path):
        print(f"Error: Configuration file not found at {config_path}", file=sys.stderr)
        sys.exit(1)

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        if not config:
            print(f"Error: Configuration file {config_path} is empty or invalid.", file=sys.stderr)
            sys.exit(1)
        print("Configuration loaded successfully.")
        # Basic validation (can be expanded)
        if 'llm' not in config or 'data_sources' not in config or 'posting' not in config:
             print(f"Warning: Config file {config_path} seems incomplete. Missing top-level keys: llm, data_sources, or posting.", file=sys.stderr)
        return config
    except yaml.YAMLError as e:
        print(f"Error parsing configuration file {config_path}: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred loading configuration: {e}", file=sys.stderr)
        sys.exit(1)

def get_secret(env_var_name: str | None) -> str | None:
    """Lấy giá trị secret từ biến môi trường một cách an toàn."""
    if not env_var_name:
        print(f"Warning: Environment variable name not specified in config.", file=sys.stderr)
        return None
    secret = os.environ.get(env_var_name)
    if not secret:
        print(f"Warning: Environment variable '{env_var_name}' not found or empty.", file=sys.stderr)
    return secret

if __name__ == '__main__':
    print("Testing config loader...")
    cfg = load_config()
    if cfg:
        print("Config loaded:")
        import json
        print(json.dumps(cfg, indent=2, ensure_ascii=False))
        print("\nTesting secret retrieval...")
        test_secret_var = cfg.get('data_sources', {}).get('github', {}).get('pat_env_var')
        if test_secret_var:
            secret_value = get_secret(test_secret_var)
            if secret_value:
                print(f"Secret for {test_secret_var} retrieved (value hidden).")
            else:
                print(f"Failed to retrieve secret for {test_secret_var}.")
        else:
            print("Could not find 'pat_env_var' in config for testing secret retrieval.")
