"""
GitHub Loader - Clone and manage GitHub repositories for analysis
"""

import os
import shutil
import tempfile
from typing import Optional
from urllib.parse import urlparse

from git import Repo


class GitHubLoader:
    """
    Loads GitHub repositories for code analysis.

    Usage:
        loader = GitHubLoader()
        repo_path = loader.clone("https://github.com/user/repo")
        # ... analyze the repo ...
        loader.cleanup()
    """

    def __init__(self, cache_dir: Optional[str] = None):
        """
        Initialize the loader.

        Args:
            cache_dir: Directory to cache cloned repos. If None, uses temp directory.
        """
        self.cache_dir = cache_dir or tempfile.mkdtemp(prefix="code-flow-")
        self._cloned_repos: list = []

    def clone(self, url: str, branch: Optional[str] = None, depth: int = 1) -> str:
        """
        Clone a GitHub repository.

        Args:
            url: GitHub repository URL (https or git@)
            branch: Specific branch to clone. If None, uses default branch.
            depth: Clone depth for shallow clones. Use 0 for full history.

        Returns:
            Path to the cloned repository
        """
        repo_name = self._extract_repo_name(url)
        repo_path = os.path.join(self.cache_dir, repo_name)

        # Remove existing clone if present
        if os.path.exists(repo_path):
            shutil.rmtree(repo_path)

        # Clone options
        clone_kwargs = {"url": url, "to_path": repo_path}
        if branch:
            clone_kwargs["branch"] = branch
        if depth > 0:
            clone_kwargs["depth"] = depth

        Repo.clone_from(**clone_kwargs)
        self._cloned_repos.append(repo_path)

        return repo_path

    def load_local(self, path: str) -> str:
        """
        Load a local repository or directory.

        Args:
            path: Path to local repository or directory

        Returns:
            Absolute path to the repository
        """
        abs_path = os.path.abspath(path)
        if not os.path.exists(abs_path):
            raise ValueError(f"Path does not exist: {path}")
        return abs_path

    def _extract_repo_name(self, url: str) -> str:
        """Extract repository name from URL"""
        # Handle SSH URLs: git@github.com:user/repo.git
        if url.startswith("git@"):
            path = url.split(":")[-1]
        else:
            # Handle HTTPS URLs: https://github.com/user/repo.git
            parsed = urlparse(url)
            path = parsed.path

        # Remove .git suffix and leading slash
        repo_name = path.strip("/").rstrip(".git")

        # Replace slashes with underscores for flat directory structure
        return repo_name.replace("/", "_")

    def cleanup(self) -> None:
        """Remove all cloned repositories"""
        for repo_path in self._cloned_repos:
            if os.path.exists(repo_path):
                shutil.rmtree(repo_path)
        self._cloned_repos = []

    def cleanup_cache(self) -> None:
        """Remove the entire cache directory"""
        if os.path.exists(self.cache_dir):
            shutil.rmtree(self.cache_dir)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
        return False


def is_github_url(url: str) -> bool:
    """Check if a URL is a GitHub repository URL"""
    if url.startswith("git@github.com:"):
        return True
    parsed = urlparse(url)
    return parsed.netloc in ("github.com", "www.github.com")


def normalize_github_url(url: str) -> str:
    """Normalize a GitHub URL to HTTPS format"""
    if url.startswith("git@github.com:"):
        # Convert SSH to HTTPS
        path = url.split(":")[-1]
        return f"https://github.com/{path}"
    return url
