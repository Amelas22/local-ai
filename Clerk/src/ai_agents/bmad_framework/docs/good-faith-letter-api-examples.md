# Good Faith Letter API Examples

## Complete Workflow Example

### 1. Generate Federal Good Faith Letter

```bash
curl -X POST http://localhost:8000/api/agents/good-faith-letter/generate-letter \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "X-Case-ID: smith-v-jones-2024" \
  -H "Content-Type: application/json" \
  -d '{
    "report_id": "789e0123-e89b-12d3-a456-426614174000",
    "jurisdiction": "federal",
    "include_evidence": true,
    "evidence_format": "inline",
    "attorney_info": {
      "name": "Jane Smith, Esq.",
      "title": "Partner",
      "firm": "Smith & Associates, P.A.",
      "bar_number": "12345",
      "address": [
        "123 Main Street",
        "Suite 400",
        "Miami, FL 33131"
      ],
      "phone": "(305) 555-1234",
      "email": "jsmith@smithlaw.com"
    },
    "additional_variables": {
      "OPPOSING_COUNSEL_NAME": "John Doe, Esq.",
      "ADDITIONAL_COUNSEL_NAMES": "Mary Johnson, Esq.",
      "OPPOSING_LAW_FIRM": "Doe & Partners, LLP",
      "ADDRESS_LINE1": "456 Court Street",
      "ADDRESS_LINE2": "Floor 10",
      "CITY": "Miami",
      "STATE": "FL",
      "ZIP": "33132",
      "SALUTATION": "Counsel",
      "LETTER_DATE": "January 20, 2024",
      "CLIENT_REFERENCE": "Defendants'",
      "REQUESTING_PARTY": "Plaintiff",
      "SPECIFIC_DISCOVERY_REFERENCES": "Requests for Production Nos. 1-25",
      "PARTY_NAME": "Defendants",
      "RTP_SET": "First Request for Production of Documents"
    }
  }'
```

### 2. Generate State-Specific Letter (Florida)

```javascript
// Using JavaScript/Node.js with axios
const axios = require('axios');

async function generateFloridaLetter() {
  const response = await axios.post(
    'http://localhost:8000/api/agents/good-faith-letter/generate-letter',
    {
      report_id: '789e0123-e89b-12d3-a456-426614174000',
      jurisdiction: 'state',
      state_code: 'FL',
      include_evidence: true,
      evidence_format: 'footnote',
      attorney_info: {
        name: 'Robert Johnson, Esq.',
        title: 'Managing Partner',
        firm: 'Johnson & Williams, P.A.',
        bar_number: '67890',
        address: [
          '789 Biscayne Boulevard',
          'Suite 2000',
          'Miami, FL 33131'
        ],
        phone: '(305) 555-5678',
        email: 'rjohnson@johnsonlaw.com'
      },
      additional_variables: {
        OPPOSING_COUNSEL_NAME: 'Sarah Davis, Esq.',
        OPPOSING_LAW_FIRM: 'Davis Legal Group',
        SALUTATION: 'Ms. Davis',
        LETTER_DATE: 'January 20, 2024',
        // Florida-specific 10-day deadline
        RESPONSE_DEADLINE: 'January 30, 2024'
      }
    },
    {
      headers: {
        'Authorization': 'Bearer YOUR_TOKEN',
        'X-Case-ID': 'johnson-v-williams-2024'
      }
    }
  );
  
  return response.data;
}
```

### 3. Customize Letter Content

```python
# Using Python with requests
import requests

def customize_letter(letter_id, token, case_id):
    url = f"http://localhost:8000/api/agents/good-faith-letter/customize/{letter_id}"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Case-ID": case_id,
        "Content-Type": "application/json"
    }
    
    edits = {
        "section_edits": [
            {
                "section": "opening_paragraph",
                "content": """Dear Counsel:

I am writing to address the significant deficiencies in your client's 
responses to Plaintiff's First Request for Production of Documents. 
Despite our previous correspondence on this matter, numerous requests 
remain unanswered or inadequately responded to."""
            },
            {
                "section": "meet_and_confer",
                "content": """My office has attempted to reach yours on multiple 
occasions to discuss these deficiencies. We remain available for a 
meet and confer conference at your earliest convenience. Please contact 
my assistant at (305) 555-1234 to schedule a call this week."""
            }
        ],
        "editor_notes": "Strengthened opening, added specific meet and confer details"
    }
    
    response = requests.put(url, json=edits, headers=headers)
    return response.json()
```

### 4. Batch Operations Example

```typescript
// TypeScript example for processing multiple deficiency reports
interface LetterGenerationParams {
  reportId: string;
  caseId: string;
  attorneyInfo: AttorneyInfo;
}

async function generateMultipleLetters(
  params: LetterGenerationParams[]
): Promise<GeneratedLetter[]> {
  const results: GeneratedLetter[] = [];
  
  for (const param of params) {
    try {
      const response = await fetch(
        '/api/agents/good-faith-letter/generate-letter',
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${getToken()}`,
            'X-Case-ID': param.caseId,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            report_id: param.reportId,
            jurisdiction: 'federal',
            include_evidence: true,
            attorney_info: param.attorneyInfo,
            additional_variables: getStandardVariables()
          })
        }
      );
      
      const letter = await response.json();
      results.push(letter);
      
      // Respect rate limits
      await sleep(6000); // 10 per minute limit
      
    } catch (error) {
      console.error(`Failed to generate letter for ${param.reportId}:`, error);
    }
  }
  
  return results;
}
```

### 5. WebSocket Integration Example

```javascript
// Real-time monitoring with Socket.io
const io = require('socket.io-client');
const socket = io('http://localhost:8000');

// Subscribe to case-specific events
socket.emit('subscribe', { case_id: 'smith-v-jones-2024' });

// Monitor letter generation
socket.on('agent:activated', (data) => {
  console.log('Agent activated:', data);
});

socket.on('letter:generation_started', (data) => {
  console.log(`Generating letter for report: ${data.report_id}`);
});

socket.on('letter:template_selected', (data) => {
  console.log(`Using ${data.jurisdiction} template`);
});

socket.on('letter:variables_mapped', (data) => {
  console.log(`Mapped ${data.variable_count} template variables`);
});

socket.on('letter:draft_created', (data) => {
  console.log(`Draft created with ID: ${data.letter_id}`);
  // Auto-preview the draft
  previewLetter(data.letter_id);
});

socket.on('letter:customization_applied', (data) => {
  console.log(`Letter updated to version ${data.version}`);
});

socket.on('letter:finalized', (data) => {
  console.log(`Letter finalized and ready for export`);
  // Auto-export to PDF
  exportLetter(data.letter_id, 'pdf');
});
```

### 6. Error Handling Example

```python
import requests
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)

class GoodFaithLetterClient:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {token}"
        }
    
    def generate_letter(
        self, 
        report_id: str, 
        case_id: str,
        **kwargs
    ) -> Optional[Dict]:
        """Generate letter with comprehensive error handling."""
        
        self.headers["X-Case-ID"] = case_id
        
        try:
            response = requests.post(
                f"{self.base_url}/api/agents/good-faith-letter/generate-letter",
                json={
                    "report_id": report_id,
                    **kwargs
                },
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            
            elif response.status_code == 400:
                error = response.json()
                logger.error(f"Bad request: {error.get('detail')}")
                
                # Handle specific errors
                if "Invalid jurisdiction" in error.get('detail', ''):
                    logger.info("Retrying with 'federal' jurisdiction")
                    kwargs['jurisdiction'] = 'federal'
                    return self.generate_letter(report_id, case_id, **kwargs)
                    
            elif response.status_code == 403:
                logger.error("Permission denied for case")
                
            elif response.status_code == 404:
                logger.error(f"Report {report_id} not found")
                
            elif response.status_code == 429:
                # Rate limited
                retry_after = response.headers.get('Retry-After', 60)
                logger.warning(f"Rate limited, retry after {retry_after}s")
                
            elif response.status_code == 500:
                logger.error("Server error, please retry")
                
        except requests.exceptions.Timeout:
            logger.error("Request timed out")
        except requests.exceptions.ConnectionError:
            logger.error("Connection failed")
        except Exception as e:
            logger.exception(f"Unexpected error: {e}")
            
        return None
```

### 7. Complete Workflow Script

```bash
#!/bin/bash
# complete-letter-workflow.sh

# Configuration
API_BASE="http://localhost:8000"
TOKEN="YOUR_AUTH_TOKEN"
CASE_ID="smith-v-jones-2024"
REPORT_ID="789e0123-e89b-12d3-a456-426614174000"

# Step 1: Generate letter
echo "Generating Good Faith letter..."
RESPONSE=$(curl -s -X POST "$API_BASE/api/agents/good-faith-letter/generate-letter" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Case-ID: $CASE_ID" \
  -H "Content-Type: application/json" \
  -d @letter-params.json)

LETTER_ID=$(echo $RESPONSE | jq -r '.letter_id')
echo "Letter created: $LETTER_ID"

# Step 2: Preview
echo "Previewing letter..."
curl -s "$API_BASE/api/agents/good-faith-letter/preview/$LETTER_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Case-ID: $CASE_ID" | jq '.content' | less

# Step 3: Ask for approval
read -p "Approve letter? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Step 4: Finalize
    echo "Finalizing letter..."
    FINALIZE_RESPONSE=$(curl -s -X POST \
      "$API_BASE/api/agents/good-faith-letter/finalize/$LETTER_ID" \
      -H "Authorization: Bearer $TOKEN" \
      -H "X-Case-ID: $CASE_ID" \
      -H "Content-Type: application/json" \
      -d '{
        "approved_by": "senior.partner@firm.com",
        "export_formats": ["pdf", "docx"]
      }')
    
    # Step 5: Download PDF
    echo "Downloading PDF..."
    curl -s "$API_BASE/api/agents/good-faith-letter/export/$LETTER_ID/pdf" \
      -H "Authorization: Bearer $TOKEN" \
      -H "X-Case-ID: $CASE_ID" \
      -o "good-faith-letter-$LETTER_ID.pdf"
    
    echo "Letter saved as: good-faith-letter-$LETTER_ID.pdf"
else
    echo "Letter not approved. Edit using customize endpoint."
fi
```

## Common Integration Patterns

### React Hook Example

```typescript
// useGoodFaithLetter.ts
import { useState, useCallback } from 'react';
import { useAuth } from './useAuth';
import { useCase } from './useCase';

export function useGoodFaithLetter() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { token } = useAuth();
  const { caseId } = useCase();
  
  const generateLetter = useCallback(async (
    reportId: string,
    options: LetterOptions
  ) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(
        '/api/agents/good-faith-letter/generate-letter',
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'X-Case-ID': caseId,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            report_id: reportId,
            ...options
          })
        }
      );
      
      if (!response.ok) {
        throw new Error(`Generation failed: ${response.statusText}`);
      }
      
      return await response.json();
      
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [token, caseId]);
  
  return { generateLetter, loading, error };
}
```

### Django Integration

```python
# views.py
from django.views import View
from django.http import JsonResponse
import requests

class GoodFaithLetterProxy(View):
    """Proxy Good Faith Letter API calls with Django auth."""
    
    def post(self, request, action):
        # Verify Django user has case access
        case_id = request.headers.get('X-Case-ID')
        if not request.user.has_case_access(case_id):
            return JsonResponse({'error': 'Forbidden'}, status=403)
        
        # Proxy to Clerk API
        clerk_url = f"http://clerk-api:8000/api/agents/good-faith-letter/{action}"
        
        response = requests.post(
            clerk_url,
            json=request.json,
            headers={
                'Authorization': f'Bearer {get_clerk_token()}',
                'X-Case-ID': case_id
            }
        )
        
        return JsonResponse(response.json(), status=response.status_code)
```