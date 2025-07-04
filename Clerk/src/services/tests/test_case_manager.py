"""
Tests for Case Management Service.
Tests case CRUD operations, validation, and access control.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from uuid import uuid4

from src.services.case_manager import CaseManager, case_manager
from src.models.case_models import Case, CaseStatus, CaseContext


@pytest.fixture
def mock_supabase_client():
    """Mock Supabase client for testing"""
    client = MagicMock()
    return client


@pytest.fixture
def case_manager_instance(mock_supabase_client):
    """Create CaseManager instance with mocked client"""
    manager = CaseManager()
    manager._client = mock_supabase_client
    return manager


class TestCaseNameToCollection:
    """Test case name to collection name conversion"""
    
    def test_simple_case_name(self, case_manager_instance):
        """Test conversion of simple case name"""
        result = case_manager_instance.case_name_to_collection(
            "Smith v Jones",
            "law-firm-123"
        )
        assert result.startswith("smith_v_jones_")
        assert len(result) <= 63
        assert result.replace("_", "").replace("-", "").isalnum()
    
    def test_special_characters_removal(self, case_manager_instance):
        """Test removal of special characters"""
        result = case_manager_instance.case_name_to_collection(
            "Smith & Jones, LLC vs. ABC Corp.",
            "law-firm-123"
        )
        assert "&" not in result
        assert "," not in result
        assert "." not in result
        assert result.startswith("smith___jones__llc_vs__abc_corp_")
    
    def test_long_case_name_truncation(self, case_manager_instance):
        """Test truncation of long case names"""
        long_name = "A" * 100
        result = case_manager_instance.case_name_to_collection(
            long_name,
            "law-firm-123"
        )
        assert len(result) <= 63
        assert result.startswith("a" * 50)  # First 50 chars preserved
    
    def test_consistent_hashing(self, case_manager_instance):
        """Test that same inputs produce same output"""
        name1 = case_manager_instance.case_name_to_collection(
            "Test Case",
            "law-firm-123"
        )
        name2 = case_manager_instance.case_name_to_collection(
            "Test Case",
            "law-firm-123"
        )
        assert name1 == name2
    
    def test_different_law_firms_different_collections(self, case_manager_instance):
        """Test that same case name in different firms gets different collection"""
        name1 = case_manager_instance.case_name_to_collection(
            "Test Case",
            "law-firm-123"
        )
        name2 = case_manager_instance.case_name_to_collection(
            "Test Case",
            "law-firm-456"
        )
        assert name1 != name2


class TestCreateCase:
    """Test case creation functionality"""
    
    @pytest.mark.asyncio
    async def test_create_case_success(self, case_manager_instance, mock_supabase_client):
        """Test successful case creation"""
        # Mock responses
        mock_supabase_client.table.return_value.insert.return_value.execute.return_value.data = [{
            "id": "case-123",
            "name": "Test Case",
            "law_firm_id": "firm-123",
            "collection_name": "test_case_abc123",
            "status": "active",
            "created_by": "user-123",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "metadata": {}
        }]
        
        # Mock get_case_by_name to return None (no existing case)
        with patch.object(case_manager_instance, 'get_case_by_name', return_value=None):
            with patch.object(case_manager_instance, '_grant_case_permission', return_value=True):
                result = await case_manager_instance.create_case(
                    name="Test Case",
                    law_firm_id="firm-123",
                    created_by="user-123"
                )
        
        assert isinstance(result, Case)
        assert result.name == "Test Case"
        assert result.law_firm_id == "firm-123"
        assert result.status == CaseStatus.ACTIVE
    
    @pytest.mark.asyncio
    async def test_create_case_empty_name(self, case_manager_instance):
        """Test case creation with empty name"""
        with pytest.raises(ValueError, match="Case name cannot be empty"):
            await case_manager_instance.create_case(
                name="",
                law_firm_id="firm-123",
                created_by="user-123"
            )
    
    @pytest.mark.asyncio
    async def test_create_case_name_too_long(self, case_manager_instance):
        """Test case creation with name exceeding 50 characters"""
        long_name = "A" * 51
        with pytest.raises(ValueError, match="Case name too long"):
            await case_manager_instance.create_case(
                name=long_name,
                law_firm_id="firm-123",
                created_by="user-123"
            )
    
    @pytest.mark.asyncio
    async def test_create_case_duplicate_name(self, case_manager_instance):
        """Test case creation with duplicate name"""
        existing_case = Case(
            id="existing-123",
            name="Existing Case",
            law_firm_id="firm-123",
            collection_name="existing_case_abc",
            status=CaseStatus.ACTIVE,
            created_by="user-123",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            metadata={}
        )
        
        with patch.object(case_manager_instance, 'get_case_by_name', return_value=existing_case):
            with pytest.raises(ValueError, match="already exists"):
                await case_manager_instance.create_case(
                    name="Existing Case",
                    law_firm_id="firm-123",
                    created_by="user-123"
                )


class TestGetUserCases:
    """Test getting user cases"""
    
    @pytest.mark.asyncio
    async def test_get_user_cases_success(self, case_manager_instance, mock_supabase_client):
        """Test successful retrieval of user cases"""
        mock_data = [
            {
                "id": "case-1",
                "name": "Case 1",
                "law_firm_id": "firm-123",
                "collection_name": "case_1_abc",
                "status": "active",
                "created_by": "user-123",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "metadata": {}
            },
            {
                "id": "case-2",
                "name": "Case 2",
                "law_firm_id": "firm-123",
                "collection_name": "case_2_def",
                "status": "active",
                "created_by": "user-123",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "metadata": {}
            }
        ]
        
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = mock_data
        
        result = await case_manager_instance.get_user_cases("user-123")
        
        assert len(result) == 2
        assert all(isinstance(case, Case) for case in result)
        assert result[0].name == "Case 1"
        assert result[1].name == "Case 2"
    
    @pytest.mark.asyncio
    async def test_get_user_cases_with_filters(self, case_manager_instance, mock_supabase_client):
        """Test getting user cases with filters"""
        mock_query = MagicMock()
        mock_supabase_client.table.return_value.select.return_value = mock_query
        mock_query.eq.return_value = mock_query
        mock_query.neq.return_value = mock_query
        mock_query.execute.return_value.data = []
        
        await case_manager_instance.get_user_cases(
            user_id="user-123",
            law_firm_id="firm-123",
            status=CaseStatus.ACTIVE
        )
        
        # Verify filters were applied
        mock_query.eq.assert_any_call("status", "active")
    
    @pytest.mark.asyncio
    async def test_get_user_cases_error_handling(self, case_manager_instance, mock_supabase_client):
        """Test error handling when getting user cases"""
        mock_supabase_client.table.side_effect = Exception("Database error")
        
        result = await case_manager_instance.get_user_cases("user-123")
        
        assert result == []  # Should return empty list on error


class TestValidateCaseAccess:
    """Test case access validation"""
    
    @pytest.mark.asyncio
    async def test_validate_access_granted(self, case_manager_instance, mock_supabase_client):
        """Test validation when access is granted"""
        mock_permission = {
            "user_id": "user-123",
            "case_id": "case-123",
            "permission_level": "write",
            "expires_at": None
        }
        
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [mock_permission]
        
        result = await case_manager_instance.validate_case_access(
            case_id="case-123",
            user_id="user-123",
            required_permission="read"
        )
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_validate_access_denied_no_permission(self, case_manager_instance, mock_supabase_client):
        """Test validation when no permission exists"""
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
        
        result = await case_manager_instance.validate_case_access(
            case_id="case-123",
            user_id="user-123",
            required_permission="read"
        )
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_validate_access_expired_permission(self, case_manager_instance, mock_supabase_client):
        """Test validation when permission is expired"""
        expired_time = (datetime.now() - timedelta(days=1)).isoformat() + "+00:00"
        mock_permission = {
            "user_id": "user-123",
            "case_id": "case-123",
            "permission_level": "read",
            "expires_at": expired_time
        }
        
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [mock_permission]
        
        result = await case_manager_instance.validate_case_access(
            case_id="case-123",
            user_id="user-123",
            required_permission="read"
        )
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_validate_access_permission_hierarchy(self, case_manager_instance, mock_supabase_client):
        """Test permission hierarchy (admin > write > read)"""
        mock_permission = {
            "user_id": "user-123",
            "case_id": "case-123",
            "permission_level": "read",
            "expires_at": None
        }
        
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [mock_permission]
        
        # Read permission should not grant write access
        result = await case_manager_instance.validate_case_access(
            case_id="case-123",
            user_id="user-123",
            required_permission="write"
        )
        
        assert result is False


class TestGetCaseContext:
    """Test getting case context"""
    
    @pytest.mark.asyncio
    async def test_get_case_context_success(self, case_manager_instance, mock_supabase_client):
        """Test successful case context retrieval"""
        mock_case = {
            "id": "case-123",
            "name": "Test Case",
            "law_firm_id": "firm-123",
            "law_firms": {"id": "firm-123", "name": "Test Firm"}
        }
        
        mock_permissions = [
            {"permission_level": "admin"},
            {"permission_level": "write"}
        ]
        
        # Mock case query
        case_query = MagicMock()
        case_query.eq.return_value.single.return_value.execute.return_value.data = mock_case
        mock_supabase_client.table.return_value.select.side_effect = [case_query, MagicMock()]
        
        # Mock permissions query
        perm_query = MagicMock()
        perm_query.eq.return_value.eq.return_value.execute.return_value.data = mock_permissions
        mock_supabase_client.table.return_value.select.side_effect = [case_query, perm_query]
        
        result = await case_manager_instance.get_case_context(
            case_id="case-123",
            user_id="user-123"
        )
        
        assert isinstance(result, CaseContext)
        assert result.case_id == "case-123"
        assert result.case_name == "Test Case"
        assert result.law_firm_id == "firm-123"
        assert "admin" in result.permissions
        assert "write" in result.permissions


class TestCaseManagerIntegration:
    """Integration tests for case manager"""
    
    def test_singleton_instance(self):
        """Test that case_manager is a singleton instance"""
        from src.services.case_manager import case_manager
        assert isinstance(case_manager, CaseManager)
    
    @patch('src.services.case_manager.settings')
    def test_initialization_without_credentials(self, mock_settings):
        """Test initialization when Supabase credentials are missing"""
        mock_settings.supabase.url = ""
        mock_settings.supabase.anon_key = ""
        
        manager = CaseManager()
        assert manager._client is None