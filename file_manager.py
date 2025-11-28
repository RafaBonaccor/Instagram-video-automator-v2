"""
Centralized File Path Management

This module provides centralized path management for replay files and data files,
making it easy to organize and access JSON files throughout the project.
"""

from pathlib import Path


class FileManager:
    """Centralized file path management for replay files"""
    
    BASE_DIR = Path(__file__).parent
    REPLAY_DIR = BASE_DIR / "replay_files"
    
    # Default files
    DEFAULT_REPLAY = REPLAY_DIR / "actions.json"
    
    # Data files (stay in root)
    INSTAGRAM_URLS = BASE_DIR / "instagram_urls.json"
    VIDEOS_DESC = BASE_DIR / "videos_and_descriptions.json"
    
    @classmethod
    def ensure_directories(cls):
        """Create replay_files directory if it doesn't exist"""
        cls.REPLAY_DIR.mkdir(exist_ok=True)
        print(f"✓ Ensured directory exists: {cls.REPLAY_DIR}")
    
    @classmethod
    def get_replay_files(cls):
        """
        Get list of all replay JSON files.
        
        Returns:
            List of Path objects for all .json files in replay_files/
        """
        if not cls.REPLAY_DIR.exists():
            return []
        return sorted(cls.REPLAY_DIR.glob("*.json"))
    
    @classmethod
    def get_replay_path(cls, filename):
        """
        Get full path for replay file.
        
        Args:
            filename: String filename or Path object
            
        Returns:
            Path object for the replay file
        """
        if isinstance(filename, str):
            filename = Path(filename)
        
        # If already absolute path, return as-is
        if filename.is_absolute():
            return filename
        
        # Otherwise, assume it's in replay_files/
        return cls.REPLAY_DIR / filename.name
    
    @classmethod
    def list_replay_files(cls):
        """
        Get list of replay file names (for display in UI).
        
        Returns:
            List of filename strings
        """
        files = cls.get_replay_files()
        return [f.name for f in files]


if __name__ == "__main__":
    # Test the file manager
    print("FileManager Test")
    print("=" * 50)
    print(f"Base directory: {FileManager.BASE_DIR}")
    print(f"Replay directory: {FileManager.REPLAY_DIR}")
    print(f"Default replay file: {FileManager.DEFAULT_REPLAY}")
    print(f"Instagram URLs: {FileManager.INSTAGRAM_URLS}")
    print(f"Videos & Descriptions: {FileManager.VIDEOS_DESC}")
    print()
    
    # Ensure directories
    FileManager.ensure_directories()
    
    # List replay files
    print("Replay files found:")
    for f in FileManager.get_replay_files():
        print(f"  - {f.name}")
