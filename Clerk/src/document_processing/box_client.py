"""
Box API client for accessing and downloading case documents.
Handles authentication, folder traversal, and file downloads.
"""

import io
import logging
from typing import Dict, List, Optional, Tuple, Generator
from dataclasses import dataclass
from datetime import datetime

from boxsdk import Client, JWTAuth
from boxsdk.object.file import File as BoxFile
from typing import BinaryIO

from config.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class BoxDocument:
    """Represents a document from Box"""

    file_id: str
    name: str
    path: str
    case_name: str
    size: int
    modified_at: datetime
    parent_folder_id: str
    folder_path: List[str]
    subfolder_name: Optional[str] = None  # Track immediate parent subfolder


class BoxClient:
    """Manages Box API connections and file operations"""

    def __init__(self):
        """Initialize Box client with JWT authentication"""
        self.client = self._create_client()

    def _create_client(self) -> Client:
        """Create authenticated Box client"""
        try:
            config_dict = self._create_config_dict()
            auth = JWTAuth.from_settings_dictionary(config_dict)
            client = Client(auth)

            # Test connection
            current_user = client.user().get()
            logger.info(f"Successfully connected to Box as {current_user.name}")

            return client

        except Exception as e:
            logger.error(f"Failed to create Box client: {str(e)}")
            raise

    def _create_config_dict(self) -> dict:
        """Create Box configuration dictionary from environment variables"""
        # Validate all required fields are present
        required_fields = {
            "client_id": settings.box.client_id,
            "client_secret": settings.box.client_secret,
            "jwt_key_id": settings.box.jwt_key_id,
            "private_key": settings.box.private_key,
            "enterprise_id": settings.box.enterprise_id,
        }

        missing_fields = [
            field for field, value in required_fields.items() if not value
        ]
        if missing_fields:
            raise ValueError(
                f"Missing required Box API configuration: {', '.join(missing_fields)}. Check your environment variables."
            )

        # Ensure private key has proper format
        private_key = settings.box.private_key
        if not private_key.startswith("-----BEGIN"):
            logger.warning(
                "Private key may not be properly formatted. Ensure it includes the full PEM headers."
            )

        config = {
            "boxAppSettings": {
                "clientID": settings.box.client_id,
                "clientSecret": settings.box.client_secret,
                "appAuth": {
                    "publicKeyID": settings.box.jwt_key_id,
                    "privateKey": private_key,
                    "passphrase": settings.box.passphrase
                    or "",  # Handle empty passphrase
                },
            },
            "enterpriseID": settings.box.enterprise_id,
        }

        return config

    def get_case_folder_info(self, folder_id: str) -> Tuple[str, str]:
        """Get case name and folder name for a given folder

        Args:
            folder_id: Box folder ID

        Returns:
            Tuple of (case_name, folder_name)
        """
        try:
            folder = self.client.folder(folder_id=folder_id).get()
            return folder.name, folder.name
        except Exception as e:
            logger.error(f"Error getting folder info: {str(e)}")
            raise

    def get_subfolders(self, parent_folder_id: str) -> List[Dict[str, str]]:
        """Get all subfolders in a parent folder

        Args:
            parent_folder_id: Parent folder ID

        Returns:
            List of folder info dictionaries
        """
        try:
            folder = self.client.folder(folder_id=parent_folder_id).get()
            subfolders = []

            for item in folder.get_items():
                if item.type == "folder":
                    subfolders.append(
                        {"id": item.id, "name": item.name, "type": item.type}
                    )

            return subfolders

        except Exception as e:
            logger.error(f"Error getting subfolders: {str(e)}")
            raise

    def traverse_folder(
        self,
        parent_folder_id: str,
        case_name: Optional[str] = None,
        parent_path: Optional[List[str]] = None,
    ) -> Generator[BoxDocument, None, None]:
        """Recursively traverse folder and yield all PDF documents

        Args:
            parent_folder_id: Box folder ID to start traversal
            case_name: Override case name (for maintaining parent case context)
            parent_path: Path components from root to maintain hierarchy

        Yields:
            BoxDocument objects for each PDF found
        """
        try:
            folder = self.client.folder(folder_id=parent_folder_id).get()

            # If no case name provided, this is the root case folder
            if case_name is None:
                case_name = folder.name
                parent_path = []
                logger.info(f"Processing case: {case_name}")

            # Build current path
            current_path = parent_path + [folder.name] if parent_path else [folder.name]

            # Determine subfolder name (immediate parent, not case root)
            subfolder_name = None
            if len(current_path) > 1:
                # This is a subfolder of the case
                subfolder_name = folder.name
                logger.info(f"Processing subfolder: {'/'.join(current_path)}")

            # Get all items in folder
            items = folder.get_items()

            for item in items:
                if item.type == "file":
                    # Check if it's a PDF
                    if item.name.lower().endswith(".pdf"):
                        file_info = self.client.file(file_id=item.id).get()

                        # Create BoxDocument with consistent case name
                        doc = BoxDocument(
                            file_id=item.id,
                            name=item.name,
                            path=f"{'/'.join(current_path)}/{item.name}",
                            case_name=case_name,  # Always use the root case name
                            size=file_info.size,
                            modified_at=datetime.fromisoformat(
                                file_info.modified_at.replace("Z", "+00:00")
                            ),
                            parent_folder_id=parent_folder_id,
                            folder_path=current_path,
                            subfolder_name=subfolder_name,  # Track immediate parent
                        )

                        yield doc

                elif item.type == "folder":
                    # Recursively process subfolders with same case name
                    yield from self.traverse_folder(
                        item.id,
                        case_name=case_name,  # Pass down the case name
                        parent_path=current_path,
                    )

        except Exception as e:
            logger.error(f"Error traversing folder {parent_folder_id}: {str(e)}")
            raise

    def upload_file(
        self,
        file_stream: BinaryIO,
        file_name: str,
        parent_folder_id: str,
        description: Optional[str] = None,
    ) -> BoxFile:
        """Upload a file to Box

        Args:
            file_stream: File content as a binary stream
            file_name: Name for the uploaded file
            parent_folder_id: Box folder ID where file should be uploaded
            description: Optional description for the file

        Returns:
            BoxFile object representing the uploaded file

        Raises:
            Exception: If upload fails
        """
        try:
            logger.info(f"Uploading file '{file_name}' to folder {parent_folder_id}")

            # Get the parent folder
            parent_folder = self.client.folder(folder_id=parent_folder_id)

            # Upload the file
            uploaded_file = parent_folder.upload_stream(
                file_stream=file_stream, file_name=file_name
            )

            logger.info(
                f"Successfully uploaded file '{file_name}' with ID: {uploaded_file.id}"
            )

            # Add description if provided
            if description:
                uploaded_file.update_info(data={"description": description})

            return uploaded_file

        except Exception as e:
            logger.error(f"Error uploading file '{file_name}': {str(e)}")
            raise

    def download_file(self, file_id: str) -> bytes:
        """Download file content from Box

        Args:
            file_id: Box file ID

        Returns:
            File content as bytes
        """
        try:
            file = self.client.file(file_id=file_id)
            content = io.BytesIO()
            file.download_to(content)
            content.seek(0)
            return content.read()

        except Exception as e:
            logger.error(f"Error downloading file {file_id}: {str(e)}")
            raise

    def get_file_info(self, file_id: str) -> Dict:
        """Get detailed file information

        Args:
            file_id: Box file ID

        Returns:
            Dictionary with file metadata
        """
        try:
            file = self.client.file(file_id=file_id).get()

            return {
                "id": file.id,
                "name": file.name,
                "size": file.size,
                "created_at": file.created_at,
                "modified_at": file.modified_at,
                "sha1": file.sha1,
                "parent": {"id": file.parent.id, "name": file.parent.name}
                if file.parent
                else None,
            }

        except Exception as e:
            logger.error(f"Error getting file info for {file_id}: {str(e)}")
            raise

    def get_shared_link(self, file_id: str) -> Optional[str]:
        """Get or create a shared link for a file

        Args:
            file_id: Box file ID

        Returns:
            Shared link URL or None
        """
        try:
            file = self.client.file(file_id=file_id).get()

            # Check if shared link exists
            if file.shared_link:
                return file.shared_link["url"]

            # Create new shared link
            shared_link = file.create_shared_link(access="open")
            return shared_link["url"]

        except Exception as e:
            logger.error(f"Error getting shared link for {file_id}: {str(e)}")
            return None

    def check_connection(self) -> bool:
        """Test Box API connection

        Returns:
            True if connection is working
        """
        try:
            self.client.user().get()
            return True
        except:
            return False
