"""
Tests for Case Context Middleware.
Tests case validation, access control, and context injection.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.datastructures import Headers

from src.middleware.case_context import (
    CaseContextMiddleware, 
    get_case_context, 
    require_case_context
)
from src.models.case_models import CaseContext


@pytest.fixture
def mock_request():
    """Create a mock request object"""
    request = Mock(spec=Request)
    request.url = Mock()
    request.url.path = "/api/search"
    request.headers = Headers({})
    request.query_params = {}
    request.state = Mock()
    request.method = "GET"
    return request


@pytest.fixture
def mock_case_manager():
    """Mock case manager for testing"""
    with patch('src.middleware.case_context.case_manager') as mock:
        mock.validate_case_access = AsyncMock(return_value=True)
        mock.get_case_context = AsyncMock(return_value=CaseContext(
            case_id="case-123",
            case_name="Test Case",
            law_firm_id="firm-123",
            user_id="user-123",
            permissions=["read", "write"]
        ))
        yield mock


@pytest.fixture
def middleware():
    """Create middleware instance"""
    app = Mock()
    return CaseContextMiddleware(app)


class TestCaseContextMiddleware:
    """Test case context middleware functionality"""
    
    @pytest.mark.asyncio
    async def test_exempt_path_bypasses_validation(self, middleware, mock_request):
        """Test that exempt paths bypass case validation"""
        mock_request.url.path = "/health"
        call_next = AsyncMock(return_value=JSONResponse({"status": "ok"}))
        
        response = await middleware.dispatch(mock_request, call_next)
        
        call_next.assert_called_once_with(mock_request)
        assert not hasattr(mock_request.state, 'case_context')
    
    @pytest.mark.asyncio
    async def test_non_case_path_bypasses_validation(self, middleware, mock_request):
        """Test that non-case paths bypass validation"""
        mock_request.url.path = "/some/other/path"
        call_next = AsyncMock(return_value=JSONResponse({"status": "ok"}))
        
        response = await middleware.dispatch(mock_request, call_next)
        
        call_next.assert_called_once_with(mock_request)
        assert not hasattr(mock_request.state, 'case_context')
    
    @pytest.mark.asyncio
    async def test_missing_case_id_returns_400(self, middleware, mock_request):
        """Test that missing case ID returns 400 error"""
        mock_request.headers = Headers({})
        mock_request.state.user_id = "user-123"
        
        call_next = AsyncMock()
        
        response = await middleware.dispatch(mock_request, call_next)
        
        assert response.status_code == 400
        assert "Case ID required" in response.body.decode()
        call_next.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_case_id_from_header(self, middleware, mock_request, mock_case_manager):
        """Test extracting case ID from header"""
        mock_request.headers = Headers({"X-Case-ID": "case-123"})
        mock_request.state.user_id = "user-123"
        
        call_next = AsyncMock(return_value=JSONResponse({"status": "ok"}))
        
        response = await middleware.dispatch(mock_request, call_next)
        
        mock_case_manager.validate_case_access.assert_called_once_with(
            case_id="case-123",
            user_id="user-123",
            required_permission="read"
        )
        assert mock_request.state.case_id == "case-123"
    
    @pytest.mark.asyncio
    async def test_case_id_from_query_params(self, middleware, mock_request, mock_case_manager):
        """Test extracting case ID from query parameters as fallback"""
        mock_request.query_params = {"case_id": "case-456"}
        mock_request.state.user_id = "user-123"
        
        call_next = AsyncMock(return_value=JSONResponse({"status": "ok"}))
        
        response = await middleware.dispatch(mock_request, call_next)
        
        mock_case_manager.validate_case_access.assert_called_once_with(
            case_id="case-456",
            user_id="user-123",
            required_permission="read"
        )
    
    @pytest.mark.asyncio
    async def test_missing_user_id_returns_401(self, middleware, mock_request):
        """Test that missing user ID returns 401 error"""
        mock_request.headers = Headers({"X-Case-ID": "case-123"})
        # No user_id in state
        
        call_next = AsyncMock()
        
        response = await middleware.dispatch(mock_request, call_next)
        
        assert response.status_code == 401
        assert "Authentication required" in response.body.decode()
    
    @pytest.mark.asyncio
    async def test_access_denied_returns_403(self, middleware, mock_request, mock_case_manager):
        """Test that access denied returns 403 error"""
        mock_request.headers = Headers({"X-Case-ID": "case-123"})
        mock_request.state.user_id = "user-123"
        mock_case_manager.validate_case_access.return_value = False
        
        call_next = AsyncMock()
        
        response = await middleware.dispatch(mock_request, call_next)
        
        assert response.status_code == 403
        assert "Access denied" in response.body.decode()
    
    @pytest.mark.asyncio
    async def test_case_not_found_returns_404(self, middleware, mock_request, mock_case_manager):
        """Test that case not found returns 404 error"""
        mock_request.headers = Headers({"X-Case-ID": "case-123"})
        mock_request.state.user_id = "user-123"
        mock_case_manager.get_case_context.return_value = None
        
        call_next = AsyncMock()
        
        response = await middleware.dispatch(mock_request, call_next)
        
        assert response.status_code == 404
        assert "Case not found" in response.body.decode()
    
    @pytest.mark.asyncio
    async def test_successful_case_context_injection(self, middleware, mock_request, mock_case_manager):
        """Test successful case context injection into request"""
        mock_request.headers = Headers({"X-Case-ID": "case-123"})
        mock_request.state.user_id = "user-123"
        
        mock_response = Mock()
        mock_response.headers = {}
        call_next = AsyncMock(return_value=mock_response)
        
        response = await middleware.dispatch(mock_request, call_next)
        
        # Verify context was injected
        assert mock_request.state.case_context.case_id == "case-123"
        assert mock_request.state.case_context.case_name == "Test Case"
        assert mock_request.state.case_id == "case-123"
        assert mock_request.state.case_name == "Test Case"
        
        # Verify response headers
        assert response.headers["X-Case-ID"] == "case-123"
        assert response.headers["X-Case-Name"] == "Test Case"
    
    @pytest.mark.asyncio
    async def test_cache_functionality(self, middleware, mock_request, mock_case_manager):
        """Test that access validation results are cached"""
        mock_request.headers = Headers({"X-Case-ID": "case-123"})
        mock_request.state.user_id = "user-123"
        
        call_next = AsyncMock(return_value=Mock(headers={}))
        
        # First call
        await middleware.dispatch(mock_request, call_next)
        assert mock_case_manager.validate_case_access.call_count == 1
        
        # Second call should use cache
        await middleware.dispatch(mock_request, call_next)
        assert mock_case_manager.validate_case_access.call_count == 1  # Still 1
        
        # Check cache
        cache_key = "user-123:case-123"
        assert cache_key in middleware._access_cache
    
    @pytest.mark.asyncio
    async def test_exception_handling(self, middleware, mock_request, mock_case_manager):
        """Test exception handling in middleware"""
        mock_request.headers = Headers({"X-Case-ID": "case-123"})
        mock_request.state.user_id = "user-123"
        mock_case_manager.validate_case_access.side_effect = Exception("Database error")
        
        call_next = AsyncMock()
        
        response = await middleware.dispatch(mock_request, call_next)
        
        assert response.status_code == 500
        assert "Internal server error" in response.body.decode()


class TestGetCaseContext:
    """Test get_case_context helper function"""
    
    def test_get_case_context_present(self):
        """Test getting case context when present"""
        request = Mock()
        context = CaseContext(
            case_id="case-123",
            case_name="Test Case",
            law_firm_id="firm-123",
            user_id="user-123",
            permissions=["read"]
        )
        request.state.case_context = context
        
        result = get_case_context(request)
        
        assert result == context
    
    def test_get_case_context_absent(self):
        """Test getting case context when absent"""
        request = Mock()
        request.state = Mock(spec=[])  # No case_context attribute
        
        result = get_case_context(request)
        
        assert result is None


class TestRequireCaseContext:
    """Test require_case_context dependency"""
    
    def test_require_context_present(self):
        """Test when context is present"""
        request = Mock()
        context = CaseContext(
            case_id="case-123",
            case_name="Test Case",
            law_firm_id="firm-123",
            user_id="user-123",
            permissions=["read", "write"]
        )
        request.state.case_context = context
        
        dependency = require_case_context("read")
        result = dependency(request)
        
        assert result == context
    
    def test_require_context_missing(self):
        """Test when context is missing"""
        request = Mock()
        request.state = Mock(spec=[])
        
        dependency = require_case_context("read")
        
        with pytest.raises(HTTPException) as exc:
            dependency(request)
        
        assert exc.value.status_code == 400
        assert "Case context required" in str(exc.value.detail)
    
    def test_require_write_permission_granted(self):
        """Test requiring write permission when granted"""
        request = Mock()
        context = Mock()
        context.has_permission = Mock(return_value=True)
        request.state.case_context = context
        
        dependency = require_case_context("write")
        result = dependency(request)
        
        context.has_permission.assert_called_once_with("write")
        assert result == context
    
    def test_require_write_permission_denied(self):
        """Test requiring write permission when denied"""
        request = Mock()
        context = Mock()
        context.has_permission = Mock(return_value=False)
        request.state.case_context = context
        
        dependency = require_case_context("write")
        
        with pytest.raises(HTTPException) as exc:
            dependency(request)
        
        assert exc.value.status_code == 403
        assert "Write permission required" in str(exc.value.detail)
    
    def test_require_admin_permission_denied(self):
        """Test requiring admin permission when denied"""
        request = Mock()
        context = Mock()
        context.has_permission = Mock(return_value=False)
        request.state.case_context = context
        
        dependency = require_case_context("admin")
        
        with pytest.raises(HTTPException) as exc:
            dependency(request)
        
        assert exc.value.status_code == 403
        assert "Admin permission required" in str(exc.value.detail)