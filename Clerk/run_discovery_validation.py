#!/usr/bin/env python
"""
Discovery Processing Validation Script

This script runs a comprehensive validation of the discovery processing feature
to ensure document splitting and WebSocket events are working correctly.
"""

import os
import sys
import asyncio
import subprocess
import time
import json
from datetime import datetime
import requests

# Add src to path
sys.path.insert(0, '/app')

class DiscoveryValidator:
    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "tests": {},
            "summary": {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "warnings": 0
            }
        }
    
    def log_test(self, test_name: str, status: str, message: str, details: dict = None):
        """Log a test result"""
        self.results["tests"][test_name] = {
            "status": status,
            "message": message,
            "details": details or {}
        }
        self.results["summary"]["total"] += 1
        
        if status == "PASS":
            self.results["summary"]["passed"] += 1
            print(f"✅ {test_name}: {message}")
        elif status == "FAIL":
            self.results["summary"]["failed"] += 1
            print(f"❌ {test_name}: {message}")
        elif status == "WARN":
            self.results["summary"]["warnings"] += 1
            print(f"⚠️  {test_name}: {message}")
        
        if details:
            for key, value in details.items():
                print(f"   {key}: {value}")
    
    def check_environment(self):
        """Check environment variables"""
        print("\n1️⃣  Checking Environment Variables...")
        print("-" * 60)
        
        required_vars = {
            "DISCOVERY_BOUNDARY_MODEL": "gpt-4.1-mini",
            "DISCOVERY_WINDOW_SIZE": "5",
            "DISCOVERY_WINDOW_OVERLAP": "1",
            "DISCOVERY_CONFIDENCE_THRESHOLD": "0.7",
            "OPENAI_API_KEY": None  # Just check it exists
        }
        
        all_good = True
        for var, expected in required_vars.items():
            value = os.getenv(var)
            if value is None:
                self.log_test(f"env_{var}", "FAIL", f"{var} not set")
                all_good = False
            elif expected and value != expected:
                self.log_test(f"env_{var}", "WARN", f"{var}={value} (expected {expected})")
            else:
                self.log_test(f"env_{var}", "PASS", f"{var} is set correctly")
        
        return all_good
    
    def check_services(self):
        """Check if required services are running"""
        print("\n2️⃣  Checking Services...")
        print("-" * 60)
        
        # Check FastAPI
        try:
            response = requests.get(f"{self.base_url}/health")
            if response.status_code == 200:
                self.log_test("service_fastapi", "PASS", "FastAPI is running")
            else:
                self.log_test("service_fastapi", "FAIL", f"FastAPI returned {response.status_code}")
                return False
        except Exception as e:
            self.log_test("service_fastapi", "FAIL", f"Cannot connect to FastAPI: {e}")
            return False
        
        # Check WebSocket
        try:
            response = requests.get(f"{self.base_url}/websocket/status")
            if response.status_code == 200:
                data = response.json()
                self.log_test("service_websocket", "PASS", "WebSocket server is running", data)
            else:
                self.log_test("service_websocket", "FAIL", f"WebSocket status returned {response.status_code}")
        except Exception as e:
            self.log_test("service_websocket", "FAIL", f"Cannot check WebSocket status: {e}")
        
        return True
    
    def test_discovery_splitter(self):
        """Test the discovery splitter directly"""
        print("\n3️⃣  Testing Discovery Splitter...")
        print("-" * 60)
        
        try:
            # Run the test script
            result = subprocess.run(
                ["python", "/app/test_discovery_simple.py"],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                # Parse output for segment count
                output = result.stdout
                if "Documents Found:" in output:
                    # Extract number of documents
                    for line in output.split('\n'):
                        if "Documents Found:" in line:
                            doc_count = int(line.split("Documents Found:")[1].strip().split()[0])
                            if doc_count >= 10:
                                self.log_test("splitter_test", "PASS", 
                                            f"Discovery splitter found {doc_count} documents")
                            else:
                                self.log_test("splitter_test", "WARN", 
                                            f"Discovery splitter only found {doc_count} documents (expected 10+)")
                            break
                else:
                    self.log_test("splitter_test", "FAIL", "Could not parse splitter output")
            else:
                self.log_test("splitter_test", "FAIL", f"Splitter test failed: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            self.log_test("splitter_test", "FAIL", "Splitter test timed out")
        except Exception as e:
            self.log_test("splitter_test", "FAIL", f"Error running splitter test: {e}")
    
    def test_websocket_monitor(self):
        """Run WebSocket monitor in background"""
        print("\n4️⃣  Starting WebSocket Monitor...")
        print("-" * 60)
        
        try:
            # Start WebSocket monitor as a background process
            monitor_process = subprocess.Popen(
                ["python", "/app/test_websocket_events.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Give it time to connect
            time.sleep(2)
            
            if monitor_process.poll() is None:
                self.log_test("websocket_monitor", "PASS", 
                            "WebSocket monitor started successfully")
                return monitor_process
            else:
                stdout, stderr = monitor_process.communicate()
                self.log_test("websocket_monitor", "FAIL", 
                            f"WebSocket monitor failed to start: {stderr}")
                return None
                
        except Exception as e:
            self.log_test("websocket_monitor", "FAIL", 
                        f"Error starting WebSocket monitor: {e}")
            return None
    
    def test_discovery_endpoint(self):
        """Test the discovery processing endpoint"""
        print("\n5️⃣  Testing Discovery Endpoint...")
        print("-" * 60)
        
        # Read test PDF
        pdf_path = "/app/tesdoc_Redacted_ocr.pdf"
        if not os.path.exists(pdf_path):
            self.log_test("discovery_endpoint", "FAIL", f"Test PDF not found: {pdf_path}")
            return None
        
        try:
            with open(pdf_path, 'rb') as f:
                pdf_content = f.read()
            
            # Prepare multipart form data
            files = {
                'discovery_files': ('tesdoc_Redacted_ocr.pdf', pdf_content, 'application/pdf')
            }
            data = {
                'production_batch': 'TEST_VALIDATION_001',
                'producing_party': 'Validation Test',
                'enable_fact_extraction': 'true'
            }
            
            # Need case context header
            headers = {
                'X-Case-ID': 'test_case_001',
                'X-Case-Name': 'Test Case Validation'
            }
            
            # Submit discovery processing request
            response = requests.post(
                f"{self.base_url}/api/discovery/process",
                files=files,
                data=data,
                headers=headers
            )
            
            if response.status_code == 200:
                result = response.json()
                processing_id = result.get('processing_id')
                self.log_test("discovery_endpoint", "PASS", 
                            f"Discovery processing started: {processing_id}")
                return processing_id
            else:
                self.log_test("discovery_endpoint", "FAIL", 
                            f"Discovery endpoint returned {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            self.log_test("discovery_endpoint", "FAIL", 
                        f"Error calling discovery endpoint: {e}")
            return None
    
    def check_processing_status(self, processing_id: str, timeout: int = 120):
        """Check processing status until complete"""
        print("\n6️⃣  Monitoring Processing Status...")
        print("-" * 60)
        
        start_time = time.time()
        last_status = None
        
        headers = {
            'X-Case-ID': 'test_case_001',
            'X-Case-Name': 'Test Case Validation'
        }
        
        while time.time() - start_time < timeout:
            try:
                response = requests.get(
                    f"{self.base_url}/api/discovery/status/{processing_id}",
                    headers=headers
                )
                
                if response.status_code == 200:
                    status = response.json()
                    current_status = status.get('status')
                    
                    if current_status != last_status:
                        print(f"   Status: {current_status}")
                        print(f"   Documents: {status.get('total_documents', 0)}")
                        print(f"   Processed: {status.get('processed_documents', 0)}")
                        print(f"   Facts: {status.get('total_facts', 0)}")
                        last_status = current_status
                    
                    if current_status == 'completed':
                        self.log_test("processing_status", "PASS", 
                                    "Processing completed successfully", status)
                        return status
                    elif current_status == 'error':
                        self.log_test("processing_status", "FAIL", 
                                    f"Processing failed: {status.get('error_message')}")
                        return None
                
            except Exception as e:
                print(f"   Error checking status: {e}")
            
            time.sleep(2)
        
        self.log_test("processing_status", "FAIL", "Processing timed out")
        return None
    
    def analyze_results(self, monitor_process):
        """Analyze WebSocket monitor results"""
        print("\n7️⃣  Analyzing Results...")
        print("-" * 60)
        
        if monitor_process:
            # Terminate monitor
            monitor_process.terminate()
            stdout, stderr = monitor_process.communicate()
            
            # Check if events log was created
            if os.path.exists('discovery_events_log.json'):
                with open('discovery_events_log.json', 'r') as f:
                    events = json.load(f)
                
                total_events = events['summary']['total_events']
                total_documents = events['summary']['total_documents']
                
                self.log_test("websocket_events", "PASS" if total_documents >= 10 else "WARN",
                            f"Received {total_events} events, found {total_documents} documents",
                            events['summary'])
                
                # Check event types
                event_counts = events['summary']['event_counts']
                expected_events = ['discovery:started', 'discovery:document_found', 'discovery:completed']
                
                for event_type in expected_events:
                    if event_type in event_counts and event_counts[event_type] > 0:
                        self.log_test(f"event_{event_type}", "PASS", 
                                    f"Received {event_counts[event_type]} {event_type} events")
                    else:
                        self.log_test(f"event_{event_type}", "FAIL", 
                                    f"No {event_type} events received")
    
    def generate_report(self):
        """Generate validation report"""
        print("\n" + "=" * 60)
        print("VALIDATION SUMMARY")
        print("=" * 60)
        
        summary = self.results["summary"]
        print(f"Total Tests: {summary['total']}")
        print(f"✅ Passed: {summary['passed']}")
        print(f"❌ Failed: {summary['failed']}")
        print(f"⚠️  Warnings: {summary['warnings']}")
        
        # Save detailed report
        report_file = f"discovery_validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print(f"\n💾 Detailed report saved to: {report_file}")
        
        # Overall result
        if summary['failed'] == 0:
            print("\n✅ VALIDATION PASSED - Discovery processing is working correctly!")
            return True
        else:
            print("\n❌ VALIDATION FAILED - Please check the failed tests above")
            return False

async def main():
    """Main validation function"""
    print("🔍 Discovery Processing Validation")
    print("=" * 60)
    print(f"Started at: {datetime.now()}")
    print("=" * 60)
    
    validator = DiscoveryValidator()
    
    # Run validation steps
    if not validator.check_environment():
        print("\n⚠️  Environment check failed. Fix environment variables first.")
        return 1
    
    if not validator.check_services():
        print("\n⚠️  Service check failed. Ensure FastAPI is running.")
        return 1
    
    # Test discovery splitter
    validator.test_discovery_splitter()
    
    # Start WebSocket monitor
    monitor_process = validator.test_websocket_monitor()
    
    # Test discovery endpoint
    processing_id = validator.test_discovery_endpoint()
    
    if processing_id:
        # Wait for processing to complete
        validator.check_processing_status(processing_id)
    
    # Give WebSocket events time to arrive
    print("\n⏳ Waiting for WebSocket events...")
    time.sleep(5)
    
    # Analyze results
    validator.analyze_results(monitor_process)
    
    # Generate report
    success = validator.generate_report()
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))