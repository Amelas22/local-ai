"""
Tests for Letter Customization Service.
"""
import pytest
from uuid import uuid4
from datetime import datetime
from unittest.mock import Mock, patch

from src.services.letter_customization_service import LetterCustomizationService
from src.models.deficiency_models import (
    GeneratedLetter,
    LetterEdit,
    LetterStatus
)


class TestLetterCustomizationService:
    """Test suite for letter customization service."""
    
    @pytest.fixture
    def service(self):
        """Create service instance."""
        return LetterCustomizationService()
    
    @pytest.fixture
    def sample_letter(self):
        """Create sample letter for testing."""
        return GeneratedLetter(
            report_id=uuid4(),
            case_name="Test_Case_2024",
            jurisdiction="federal",
            content="Dear Counsel:\n\nThis is a test letter.\n\nSincerely,\nTest Attorney",
            agent_execution_id="test-exec-123"
        )
    
    @pytest.mark.asyncio
    async def test_apply_edits_success(self, service, sample_letter):
        """Test successful edit application."""
        # Store letter
        service._letter_storage[sample_letter.id] = sample_letter
        
        # Apply edits
        edits = [
            {
                "section": "full_content",
                "content": "Dear Counsel:\n\nThis is an edited test letter with new content.\n\nSincerely,\nTest Attorney"
            }
        ]
        
        with patch('src.services.letter_customization_service.emit_agent_event'):
            result = await service.apply_edits(
                letter_id=sample_letter.id,
                section_edits=edits,
                editor_id="test-editor",
                editor_notes="Updated content"
            )
        
        # Verify
        assert result.version == 2
        assert result.status == LetterStatus.REVIEW
        assert len(result.edit_history) == 1
        assert "edited test letter" in result.content
    
    @pytest.mark.asyncio
    async def test_apply_edits_invalid_status(self, service, sample_letter):
        """Test edit fails on finalized letter."""
        sample_letter.status = LetterStatus.FINALIZED
        service._letter_storage[sample_letter.id] = sample_letter
        
        with pytest.raises(ValueError) as exc_info:
            await service.apply_edits(
                letter_id=sample_letter.id,
                section_edits=[{"section": "test", "content": "new"}],
                editor_id="test-editor"
            )
        
        assert "cannot be edited" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_apply_edits_validation_warnings(self, service, sample_letter):
        """Test content validation during edits."""
        service._letter_storage[sample_letter.id] = sample_letter
        
        # Edit with unprofessional content
        edits = [
            {
                "section": "full_content",
                "content": "Dear Counsel:\n\nYou failed to produce documents. This is bad faith.\n\nSincerely,\nAttorney"
            }
        ]
        
        with patch('src.services.letter_customization_service.emit_agent_event'):
            with patch.object(service, '_validate_content') as mock_validate:
                mock_validate.return_value = {
                    'valid': False,
                    'warnings': ['Unprofessional phrase detected']
                }
                
                result = await service.apply_edits(
                    letter_id=sample_letter.id,
                    section_edits=edits,
                    editor_id="test-editor"
                )
                
                mock_validate.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_approve_letter_success(self, service, sample_letter):
        """Test letter approval."""
        sample_letter.status = LetterStatus.REVIEW
        service._letter_storage[sample_letter.id] = sample_letter
        
        with patch('src.services.letter_customization_service.emit_agent_event'):
            result = await service.approve_letter(
                letter_id=sample_letter.id,
                approver_id="senior-attorney",
                approval_notes="Looks good"
            )
        
        assert result.status == LetterStatus.APPROVED
        assert result.approved_by == "senior-attorney"
        assert result.approved_at is not None
        assert 'approval' in result.metadata
    
    @pytest.mark.asyncio
    async def test_approve_letter_wrong_status(self, service, sample_letter):
        """Test approval fails if not in review."""
        sample_letter.status = LetterStatus.DRAFT
        service._letter_storage[sample_letter.id] = sample_letter
        
        with pytest.raises(ValueError) as exc_info:
            await service.approve_letter(
                letter_id=sample_letter.id,
                approver_id="attorney"
            )
        
        assert "must be in REVIEW status" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_revert_to_version(self, service, sample_letter):
        """Test reverting to previous version."""
        # Add edit history
        sample_letter.version = 3
        sample_letter.edit_history = [
            LetterEdit(
                section_name="full_content",
                original_content="Original",
                new_content="Edit 1",
                editor_id="editor1"
            ),
            LetterEdit(
                section_name="full_content", 
                original_content="Edit 1",
                new_content="Edit 2",
                editor_id="editor2"
            )
        ]
        sample_letter.content = "Edit 2"
        sample_letter.status = LetterStatus.REVIEW
        
        service._letter_storage[sample_letter.id] = sample_letter
        
        result = await service.revert_to_version(
            letter_id=sample_letter.id,
            version=1,
            reverter_id="supervisor",
            reason="Revert to original"
        )
        
        assert result.version == 4  # New version created
        assert len(result.edit_history) == 3  # Added reversion edit
        assert result.status == LetterStatus.REVIEW
    
    def test_get_edit_history(self, service, sample_letter):
        """Test retrieving edit history."""
        # Add edit history
        sample_letter.edit_history = [
            LetterEdit(
                section_name="opening",
                original_content="Dear Sir",
                new_content="Dear Counsel",
                editor_id="editor1",
                editor_notes="More formal"
            ),
            LetterEdit(
                section_name="body",
                original_content="Short body",
                new_content="Longer detailed body",
                editor_id="editor2"
            )
        ]
        
        service._letter_storage[sample_letter.id] = sample_letter
        
        history = service.get_edit_history(sample_letter.id)
        
        assert len(history) == 2
        assert history[0]["section"] == "opening"
        assert history[0]["editor"] == "editor1"
        assert history[0]["notes"] == "More formal"
        assert history[1]["section"] == "body"
    
    def test_get_edit_history_with_limit(self, service, sample_letter):
        """Test edit history with limit."""
        # Add many edits
        sample_letter.edit_history = [
            LetterEdit(
                section_name=f"section_{i}",
                original_content=f"orig_{i}",
                new_content=f"new_{i}",
                editor_id=f"editor_{i}"
            )
            for i in range(10)
        ]
        
        service._letter_storage[sample_letter.id] = sample_letter
        
        history = service.get_edit_history(sample_letter.id, limit=3)
        
        assert len(history) == 3
        # Should get last 3 edits
        assert history[0]["section"] == "section_7"
        assert history[2]["section"] == "section_9"
    
    @pytest.mark.asyncio
    async def test_validate_content_federal(self, service):
        """Test federal content validation."""
        content = """
        Dear Counsel:
        
        Pursuant to FRCP Rule 37, we must meet and confer regarding
        discovery deficiencies.
        
        Respectfully submitted,
        Attorney
        """
        
        result = await service._validate_content(content, "federal")
        
        assert result['valid'] is True
        assert len(result['warnings']) == 0
    
    @pytest.mark.asyncio
    async def test_validate_content_unprofessional(self, service):
        """Test validation catches unprofessional language."""
        content = """
        Dear Counsel:
        
        You failed to produce documents. Your refusal is in bad faith
        and these frivolous objections must stop.
        
        Attorney
        """
        
        result = await service._validate_content(content, "federal")
        
        assert result['valid'] is False
        assert len(result['warnings']) > 0
        assert any("you failed" in w.lower() for w in result['warnings'])
        assert any("bad faith" in w.lower() for w in result['warnings'])