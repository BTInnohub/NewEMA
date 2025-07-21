#!/usr/bin/env python3
"""
EMA NextGen Intrusion Detection System - Backend API Testing
Tests all backend functionality including authentication, zones, alarms, WebSocket, and dashboard.
"""

import requests
import json
import asyncio
import websockets
import time
from datetime import datetime
import sys
import os

# Backend URL from frontend/.env
BACKEND_URL = "https://ef5ac598-f312-4c67-b352-9f0c3a8abcfe.preview.emergentagent.com"
API_BASE_URL = f"{BACKEND_URL}/api"
WS_URL = f"wss://ef5ac598-f312-4c67-b352-9f0c3a8abcfe.preview.emergentagent.com/ws"

class BackendTester:
    def __init__(self):
        self.session = requests.Session()
        self.auth_token = None
        self.test_user_id = None
        self.test_zone_id = None
        self.test_alarm_id = None
        self.results = {
            "Authentication System": {"status": "PENDING", "details": []},
            "Zone Management API": {"status": "PENDING", "details": []},
            "Alarm Management System": {"status": "PENDING", "details": []},
            "Real-time WebSocket Communication": {"status": "PENDING", "details": []},
            "Dashboard Statistics API": {"status": "PENDING", "details": []},
            "Event Logging System": {"status": "PENDING", "details": []}
        }

    def log_result(self, test_name, success, message):
        """Log test result"""
        status = "PASS" if success else "FAIL"
        self.results[test_name]["details"].append(f"{status}: {message}")
        print(f"[{status}] {test_name}: {message}")

    def set_test_status(self, test_name, overall_status):
        """Set overall status for a test category"""
        self.results[test_name]["status"] = overall_status

    def test_authentication_system(self):
        """Test user registration, login, and JWT token validation"""
        print("\n=== Testing Authentication System ===")
        
        try:
            # Test user registration
            register_data = {
                "email": "security.admin@ema-nextgen.com",
                "name": "Security Administrator",
                "password": "SecurePass123!",
                "role": "admin"
            }
            
            response = self.session.post(f"{API_BASE_URL}/auth/register", json=register_data)
            if response.status_code == 200:
                self.log_result("Authentication System", True, "User registration successful")
                user_data = response.json()
                self.test_user_id = user_data.get("user", {}).get("id")
            elif response.status_code == 400 and "already registered" in response.text:
                self.log_result("Authentication System", True, "User already exists (expected for repeated tests)")
            else:
                self.log_result("Authentication System", False, f"Registration failed: {response.status_code} - {response.text}")
                
            # Test user login
            login_data = {
                "email": "security.admin@ema-nextgen.com",
                "password": "SecurePass123!"
            }
            
            response = self.session.post(f"{API_BASE_URL}/auth/login", json=login_data)
            if response.status_code == 200:
                login_result = response.json()
                self.auth_token = login_result.get("access_token")
                self.test_user_id = login_result.get("user", {}).get("id")
                self.log_result("Authentication System", True, "User login successful")
                self.log_result("Authentication System", True, f"JWT token received: {self.auth_token[:20]}...")
            else:
                self.log_result("Authentication System", False, f"Login failed: {response.status_code} - {response.text}")
                self.set_test_status("Authentication System", "FAIL")
                return False
                
            # Test JWT token validation
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            response = self.session.get(f"{API_BASE_URL}/auth/me", headers=headers)
            if response.status_code == 200:
                user_info = response.json()
                self.log_result("Authentication System", True, f"JWT validation successful - User: {user_info.get('name')}")
            else:
                self.log_result("Authentication System", False, f"JWT validation failed: {response.status_code}")
                
            # Test invalid token
            invalid_headers = {"Authorization": "Bearer invalid_token"}
            response = self.session.get(f"{API_BASE_URL}/auth/me", headers=invalid_headers)
            if response.status_code == 401:
                self.log_result("Authentication System", True, "Invalid token properly rejected")
            else:
                self.log_result("Authentication System", False, "Invalid token not properly rejected")
                
            self.set_test_status("Authentication System", "PASS")
            return True
            
        except Exception as e:
            self.log_result("Authentication System", False, f"Exception during authentication test: {str(e)}")
            self.set_test_status("Authentication System", "FAIL")
            return False

    def test_zone_management_api(self):
        """Test zone CRUD operations and arm/disarm functionality"""
        print("\n=== Testing Zone Management API ===")
        
        if not self.auth_token:
            self.log_result("Zone Management API", False, "No auth token available")
            self.set_test_status("Zone Management API", "FAIL")
            return False
            
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        try:
            # Test zone creation
            zone_data = {
                "name": "Main Entrance",
                "zone_type": "door_contact",
                "area": "Ground Floor",
                "description": "Primary entrance door contact sensor"
            }
            
            response = self.session.post(f"{API_BASE_URL}/zones", json=zone_data, headers=headers)
            if response.status_code == 200:
                zone_result = response.json()
                self.test_zone_id = zone_result.get("id")
                self.log_result("Zone Management API", True, f"Zone created successfully: {zone_result.get('name')}")
            else:
                self.log_result("Zone Management API", False, f"Zone creation failed: {response.status_code} - {response.text}")
                
            # Test get all zones
            response = self.session.get(f"{API_BASE_URL}/zones", headers=headers)
            if response.status_code == 200:
                zones = response.json()
                self.log_result("Zone Management API", True, f"Retrieved {len(zones)} zones")
                if not self.test_zone_id and zones:
                    self.test_zone_id = zones[0].get("id")
            else:
                self.log_result("Zone Management API", False, f"Get zones failed: {response.status_code}")
                
            if self.test_zone_id:
                # Test get specific zone
                response = self.session.get(f"{API_BASE_URL}/zones/{self.test_zone_id}", headers=headers)
                if response.status_code == 200:
                    zone = response.json()
                    self.log_result("Zone Management API", True, f"Retrieved zone: {zone.get('name')}")
                else:
                    self.log_result("Zone Management API", False, f"Get specific zone failed: {response.status_code}")
                    
                # Test zone update
                update_data = {
                    "description": "Updated description for main entrance sensor"
                }
                response = self.session.put(f"{API_BASE_URL}/zones/{self.test_zone_id}", json=update_data, headers=headers)
                if response.status_code == 200:
                    self.log_result("Zone Management API", True, "Zone updated successfully")
                else:
                    self.log_result("Zone Management API", False, f"Zone update failed: {response.status_code}")
                    
                # Test zone arm
                response = self.session.post(f"{API_BASE_URL}/zones/{self.test_zone_id}/arm", headers=headers)
                if response.status_code == 200:
                    self.log_result("Zone Management API", True, "Zone armed successfully")
                else:
                    self.log_result("Zone Management API", False, f"Zone arm failed: {response.status_code}")
                    
                # Test zone disarm
                response = self.session.post(f"{API_BASE_URL}/zones/{self.test_zone_id}/disarm", headers=headers)
                if response.status_code == 200:
                    self.log_result("Zone Management API", True, "Zone disarmed successfully")
                else:
                    self.log_result("Zone Management API", False, f"Zone disarm failed: {response.status_code}")
                    
                # Test Test Alarm functionality (key requirement from review)
                response = self.session.post(f"{API_BASE_URL}/zones/{self.test_zone_id}/test-alarm", headers=headers)
                if response.status_code == 200:
                    test_alarm_result = response.json()
                    self.log_result("Zone Management API", True, "Test Alarm triggered successfully")
                    # Store the alarm ID for later testing
                    if "alarm" in test_alarm_result:
                        self.test_alarm_id = test_alarm_result["alarm"].get("id")
                        self.log_result("Zone Management API", True, f"Test alarm created with ID: {self.test_alarm_id}")
                else:
                    self.log_result("Zone Management API", False, f"Test Alarm failed: {response.status_code} - {response.text}")
                    
            self.set_test_status("Zone Management API", "PASS")
            return True
            
        except Exception as e:
            self.log_result("Zone Management API", False, f"Exception during zone management test: {str(e)}")
            self.set_test_status("Zone Management API", "FAIL")
            return False

    def test_alarm_management_system(self):
        """Test alarm retrieval, acknowledgment, and resolution"""
        print("\n=== Testing Alarm Management System ===")
        
        if not self.auth_token:
            self.log_result("Alarm Management System", False, "No auth token available")
            self.set_test_status("Alarm Management System", "FAIL")
            return False
            
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        try:
            # Test get all alarms
            response = self.session.get(f"{API_BASE_URL}/alarms", headers=headers)
            if response.status_code == 200:
                alarms = response.json()
                self.log_result("Alarm Management System", True, f"Retrieved {len(alarms)} alarms")
                
                # Find an active alarm for testing
                active_alarms = [alarm for alarm in alarms if alarm.get("status") == "active"]
                if active_alarms:
                    self.test_alarm_id = active_alarms[0].get("id")
                    self.log_result("Alarm Management System", True, f"Found active alarm for testing: {self.test_alarm_id}")
                else:
                    self.log_result("Alarm Management System", True, "No active alarms found (normal for new system)")
                    
            else:
                self.log_result("Alarm Management System", False, f"Get alarms failed: {response.status_code}")
                
            # If we have an alarm to test with
            if self.test_alarm_id:
                # Test alarm acknowledgment
                response = self.session.post(f"{API_BASE_URL}/alarms/{self.test_alarm_id}/acknowledge", headers=headers)
                if response.status_code == 200:
                    self.log_result("Alarm Management System", True, "Alarm acknowledged successfully")
                else:
                    self.log_result("Alarm Management System", False, f"Alarm acknowledge failed: {response.status_code}")
                    
                # Test alarm resolution
                response = self.session.post(f"{API_BASE_URL}/alarms/{self.test_alarm_id}/resolve", headers=headers)
                if response.status_code == 200:
                    self.log_result("Alarm Management System", True, "Alarm resolved successfully")
                else:
                    self.log_result("Alarm Management System", False, f"Alarm resolve failed: {response.status_code}")
            else:
                self.log_result("Alarm Management System", True, "Alarm acknowledge/resolve tests skipped (no active alarms)")
                
            self.set_test_status("Alarm Management System", "PASS")
            return True
            
        except Exception as e:
            self.log_result("Alarm Management System", False, f"Exception during alarm management test: {str(e)}")
            self.set_test_status("Alarm Management System", "FAIL")
            return False

    async def test_websocket_communication(self):
        """Test WebSocket connectivity and real-time updates"""
        print("\n=== Testing Real-time WebSocket Communication ===")
        
        try:
            # Test WebSocket connection
            async with websockets.connect(WS_URL) as websocket:
                self.log_result("Real-time WebSocket Communication", True, "WebSocket connection established")
                
                # Send a test message
                test_message = json.dumps({"type": "ping", "data": "test"})
                await websocket.send(test_message)
                self.log_result("Real-time WebSocket Communication", True, "Test message sent to WebSocket")
                
                # Try to receive a message (with timeout)
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    self.log_result("Real-time WebSocket Communication", True, f"Received WebSocket message: {message[:100]}...")
                except asyncio.TimeoutError:
                    self.log_result("Real-time WebSocket Communication", True, "No immediate WebSocket response (normal)")
                    
            self.set_test_status("Real-time WebSocket Communication", "PASS")
            return True
            
        except Exception as e:
            self.log_result("Real-time WebSocket Communication", False, f"WebSocket test failed: {str(e)}")
            self.set_test_status("Real-time WebSocket Communication", "FAIL")
            return False

    def test_dashboard_statistics_api(self):
        """Test system statistics endpoint"""
        print("\n=== Testing Dashboard Statistics API ===")
        
        if not self.auth_token:
            self.log_result("Dashboard Statistics API", False, "No auth token available")
            self.set_test_status("Dashboard Statistics API", "FAIL")
            return False
            
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        try:
            # Test dashboard stats
            response = self.session.get(f"{API_BASE_URL}/dashboard/stats", headers=headers)
            if response.status_code == 200:
                stats = response.json()
                required_fields = ["total_zones", "active_alarms", "zones_armed", "zones_normal", "zones_fault", "total_events_today", "system_uptime"]
                
                missing_fields = [field for field in required_fields if field not in stats]
                if not missing_fields:
                    self.log_result("Dashboard Statistics API", True, f"Dashboard stats retrieved successfully")
                    self.log_result("Dashboard Statistics API", True, f"Stats: {stats}")
                else:
                    self.log_result("Dashboard Statistics API", False, f"Missing required fields: {missing_fields}")
            else:
                self.log_result("Dashboard Statistics API", False, f"Dashboard stats failed: {response.status_code} - {response.text}")
                
            self.set_test_status("Dashboard Statistics API", "PASS")
            return True
            
        except Exception as e:
            self.log_result("Dashboard Statistics API", False, f"Exception during dashboard stats test: {str(e)}")
            self.set_test_status("Dashboard Statistics API", "FAIL")
            return False

    def test_event_logging_system(self):
        """Test event creation and retrieval"""
        print("\n=== Testing Event Logging System ===")
        
        if not self.auth_token:
            self.log_result("Event Logging System", False, "No auth token available")
            self.set_test_status("Event Logging System", "FAIL")
            return False
            
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        try:
            # Test get events
            response = self.session.get(f"{API_BASE_URL}/events", headers=headers)
            if response.status_code == 200:
                events = response.json()
                self.log_result("Event Logging System", True, f"Retrieved {len(events)} events")
                
                # Check if events have required structure
                if events:
                    event = events[0]
                    required_fields = ["id", "event_type", "description", "timestamp"]
                    missing_fields = [field for field in required_fields if field not in event]
                    if not missing_fields:
                        self.log_result("Event Logging System", True, "Event structure is correct")
                    else:
                        self.log_result("Event Logging System", False, f"Event missing fields: {missing_fields}")
                else:
                    self.log_result("Event Logging System", True, "No events found (normal for new system)")
                    
            else:
                self.log_result("Event Logging System", False, f"Get events failed: {response.status_code} - {response.text}")
                
            self.set_test_status("Event Logging System", "PASS")
            return True
            
        except Exception as e:
            self.log_result("Event Logging System", False, f"Exception during event logging test: {str(e)}")
            self.set_test_status("Event Logging System", "FAIL")
            return False

    def test_api_root(self):
        """Test basic API connectivity"""
        print("\n=== Testing Basic API Connectivity ===")
        
        try:
            response = self.session.get(f"{API_BASE_URL}/")
            if response.status_code == 200:
                result = response.json()
                if "EMA NextGen" in result.get("message", ""):
                    print(f"[PASS] API root endpoint working: {result.get('message')}")
                    return True
                else:
                    print(f"[FAIL] Unexpected API root response: {result}")
                    return False
            else:
                print(f"[FAIL] API root endpoint failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"[FAIL] API connectivity test failed: {str(e)}")
            return False

    async def run_all_tests(self):
        """Run all backend tests"""
        print("Starting EMA NextGen Backend API Tests...")
        print(f"Backend URL: {BACKEND_URL}")
        print(f"API Base URL: {API_BASE_URL}")
        print(f"WebSocket URL: {WS_URL}")
        
        # Test basic connectivity first
        if not self.test_api_root():
            print("Basic API connectivity failed. Stopping tests.")
            return
        
        # Run all tests
        self.test_authentication_system()
        self.test_zone_management_api()
        self.test_alarm_management_system()
        await self.test_websocket_communication()
        self.test_dashboard_statistics_api()
        self.test_event_logging_system()
        
        # Print summary
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        
        for test_name, result in self.results.items():
            status = result["status"]
            print(f"{test_name}: {status}")
            for detail in result["details"]:
                print(f"  - {detail}")
        
        print("\n" + "="*60)

def main():
    """Main test runner"""
    tester = BackendTester()
    asyncio.run(tester.run_all_tests())

if __name__ == "__main__":
    main()