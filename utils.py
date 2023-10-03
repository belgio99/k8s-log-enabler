import os
import re

"""
Utility functions
"""
def load_manifests(filenames):
    """
    Load multiple manifest contents from a list of files.
    """
    manifests = {}
    for filename in filenames:
        if not os.path.exists(filename):
            raise FileNotFoundError(f"Error: File '{filename}' does not exist.")
        manifests[filename] = load_manifest(filename)
    return manifests


def load_manifest(filename):
    """
    Load manifest content from a file.
    """
    with open(filename, "r", encoding="utf-8") as file:
        return file.read()


def build_merged_text(manifests):
    """
    Build merged text from list of manifest texts.
    """
    return "\n---\n".join(manifests) + "\n---\n"


def is_valid_k8s_namespace(namespace_name):
    """
    Check if a given namespace name respects the Kubernetes naming requirements.

    Args:
    - namespace_name (str): The name of the namespace to be checked.

    Returns:
    - bool: True if the namespace name is valid, otherwise False.
    """
    
    if len(namespace_name) > 63:
        return False

    # Regex pattern used to match valid namespace names
    pattern = re.compile('^[a-z0-9]([-a-z0-9]*[a-z0-9])?$')
    
    return bool(pattern.match(namespace_name))

def is_valid_timeout(timeout_str):
    """
    Validates if the provided timeout string matches the Kubernetes timeout format.

    Args:
    - timeout_str (str): The timeout string to be checked.

    Returns:
    - bool: True if the timeout format is valid, otherwise False.
    """
    
    # Regex pattern to match valid timeout strings
    pattern = re.compile('^[0-9]+[hms]$')
    
    return bool(pattern.match(timeout_str))
