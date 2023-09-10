"""
Utility functions
"""
def load_manifests(filenames):
    """
    Load multiple manifest contents from a list of files.
    """
    return {filename: load_manifest(filename) for filename in filenames}


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