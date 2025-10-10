"""
ACS Courier REST API Client - CORRECTED VERSION
Follows official ACS REST API documentation (June 2024)

CRITICAL FIXES:
- Correct endpoint structure (all requests to single URL)
- Proper JSON format with ACSAlias + ACSInputParameters
- API Key in headers
- Correct field names from documentation
- Proper error handling
- Pickup list support
"""

import requests
import json
import base64
from datetime import datetime, date
from typing import Dict, List, Optional
from time import sleep


class ACSCourierAPI:
    """
    ACS Courier REST API Handler
    Based on official documentation: https://webservices.acscourier.net/ACSRestServices/swagger/
    """
    
    def __init__(self):
        """Initialize ACS API with TEST credentials"""
        
        # Single endpoint for ALL requests (from documentation page 2)
        self.base_url = "https://webservices.acscourier.net/ACSRestServices/api/ACSAutoRest"
        
        # TEST Credentials (from your email)
        self.credentials = {
            "Company_ID": "999630747_acs",
            "Company_Password": "SBBEm7T9",
            "User_ID": "apiRouS",
            "User_Password": "NJgXeHkL"
        }
        
        # API Key goes in HEADER (page 2)
        self.api_key = "5a959ce1aad74eea90a95cbc700bf32b"
        
        # Your company details (from voucher)
        self.company_data = {
            "billing_code": "2ΠΓ550690",
            "sender_name": "ROUSSAKIS SUPPLIES IKE",
            "sender_address": "Γ.ΠΑΠΑΝΔΡΕΟΥ & ΦΑΝΑΡΙΣΤΑ",
            "sender_city": "ΑΣΠΡΟΠΥΡΓΟΣ",
            "sender_zipcode": "19300",
            "sender_phone": "2105582077"
        }
        
        # Setup session with API Key header
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json; charset=utf-8',
            'Accept': 'application/json',
            'AcsApiKey': self.api_key  # CRITICAL!
        })
        
        # Rate limiting (max 10 calls/sec per documentation page 2)
        self.last_call_time = 0
        self.min_call_interval = 0.1  # 100ms between calls
    
    def _rate_limit(self):
        """Enforce rate limiting"""
        import time
        now = time.time()
        elapsed = now - self.last_call_time
        
        if elapsed < self.min_call_interval:
            sleep(self.min_call_interval - elapsed)
        
        self.last_call_time = time.time()
    
    def _make_request(self, alias: str, parameters: Dict) -> Dict:
        """
        Make ACS API request
        
        Args:
            alias: Method name (e.g., "ACS_Create_Voucher")
            parameters: Input parameters dict
            
        Returns:
            Response dict with success status and data
        """
        self._rate_limit()
        
        # Build request per documentation format (page 2)
        payload = {
            "ACSAlias": alias,
            "ACSInputParameters": {
                **self.credentials,
                **parameters
            }
        }
        
        try:
            response = self.session.post(
                self.base_url,
                json=payload,
                timeout=30
            )
            
            # Check HTTP status
            response.raise_for_status()
            
            result = response.json()
            
            # Parse response (page 2-3 format)
            if result.get('ACSExecution_HasError') == False:
                return {
                    'success': True,
                    'data': result.get('ACSOutputResponce', {})
                }
            else:
                return {
                    'success': False,
                    'error': result.get('ACSExecutionErrorMessage', 'Unknown error')
                }
        
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                return {
                    'success': False,
                    'error': 'API Key authentication failed (403 Forbidden)'
                }
            elif e.response.status_code == 406:
                return {
                    'success': False,
                    'error': 'Rate limit exceeded (406 Not Acceptable)'
                }
            else:
                return {
                    'success': False,
                    'error': f'HTTP {e.response.status_code}: {str(e)}'
                }
        
        except Exception as e:
            return {
                'success': False,
                'error': f'Request failed: {str(e)}'
            }
    
    def create_voucher(self, shipment_data: Dict) -> Dict:
        """
        Create ACS voucher
        Documentation: Page 4-8 (ACS_Create_Voucher method)
        
        Args:
            shipment_data: Shipment details
                Required:
                - recipient_name: str
                - recipient_address: str (street ONLY, no number!)
                - recipient_address_number: str
                - recipient_zipcode: str (5 digits)
                - recipient_region: str (city/area)
                - recipient_phone: str OR recipient_cell_phone: str
                
                Optional:
                - weight: float (default 0.5, min 0.5)
                - cod_amount: float (if COD)
                - delivery_notes: str
                - pieces: int (Item_Quantity, default 1)
                
        Returns:
            Dict with voucher_no or error
        """
        
        # Build parameters (EXACT field names from documentation page 5-6)
        params = {
            # Required
            "Pickup_Date": date.today().strftime('%Y-%m-%d'),
            "Sender": self.company_data['sender_name'],
            
            # Recipient (CRITICAL: Address WITHOUT number!)
            "Recipient_Name": shipment_data['recipient_name'],
            "Recipient_Address": shipment_data['recipient_address'],  # Street only!
            "Recipient_Address_Number": shipment_data.get('recipient_address_number', ''),
            "Recipient_Zipcode": shipment_data['recipient_zipcode'],
            "Recipient_Region": shipment_data['recipient_region'],  # NOT City!
            "Recipient_Country": "GR",
            
            # Phones (at least one required)
            "Recipient_Phone": shipment_data.get('recipient_phone', ''),
            "Recipient_Cell_Phone": shipment_data.get('recipient_cell_phone', ''),
            
            # Optional fields
            "Recipient_Email": shipment_data.get('recipient_email', ''),
            "Recipient_Floor": shipment_data.get('recipient_floor', ''),
            "Recipient_Company_Name": shipment_data.get('recipient_company', ''),
            
            # Billing
            "Billing_Code": self.company_data['billing_code'],
            "Charge_Type": 2,  # 2=sender pays, 4=recipient pays
            
            # Shipment details
            "Item_Quantity": shipment_data.get('pieces', 1),
            "Weight": shipment_data.get('weight', 0.5),  # Min 0.5kg
            
            # Dimensions (optional)
            "Dimension_X_In_Cm": shipment_data.get('length_cm'),
            "Dimension_Y_in_Cm": shipment_data.get('width_cm'),
            "Dimension_Z_in_Cm": shipment_data.get('height_cm'),
            
            # COD (Cash on Delivery)
            "Cod_Ammount": shipment_data.get('cod_amount', 0),
            "Cod_Payment_Way": 0 if shipment_data.get('cod_amount', 0) > 0 else None,  # 0=cash
            
            # Delivery products (page 6-7)
            "Acs_Delivery_Products": self._build_delivery_products(shipment_data),
            
            # Notes
            "Delivery_Notes": shipment_data.get('delivery_notes', ''),
            "Reference_Key1": shipment_data.get('reference1', ''),
            "Reference_Key2": shipment_data.get('reference2', ''),
            
            # Station (optional - for smart points)
            "Acs_Station_Destination": shipment_data.get('station_code'),
            "Acs_Station_Branch_Destination": shipment_data.get('branch_id', 1),
            
            # Language
            "Language": "GR"
        }
        
        # Remove None values
        params = {k: v for k, v in params.items() if v is not None}
        
        # Make request
        result = self._make_request("ACS_Create_Voucher", params)
        
        if result['success']:
            output = result['data'].get('ACSValueOutput', [])
            if output and len(output) > 0:
                voucher_info = output[0]
                
                if voucher_info.get('Voucher_No'):
                    return {
                        'success': True,
                        'voucher_no': voucher_info['Voucher_No'].strip(),
                        'voucher_no_return': voucher_info.get('Voucher_No_Return'),
                        'message': 'Voucher created successfully'
                    }
                else:
                    return {
                        'success': False,
                        'error': voucher_info.get('Error_Message', 'Voucher creation failed')
                    }
        
        return result
    
    def _build_delivery_products(self, shipment_data: Dict) -> str:
        """Build delivery products string (page 6-7)"""
        products = []
        
        # COD (Cash on Delivery)
        if shipment_data.get('cod_amount', 0) > 0:
            products.append('COD')
        
        # Additional services
        if shipment_data.get('saturday_delivery'):
            products.append('SAT')
        
        if shipment_data.get('insurance_amount'):
            products.append('INS')
        
        if shipment_data.get('morning_delivery'):
            products.append('MDV')
        
        return ','.join(products) if products else None
    
    def print_voucher(self, voucher_no: str, print_type: int = 2, 
                     output_path: str = None) -> Dict:
        """
        Print voucher as PDF
        Documentation: Page 10 (ACS_Print_Voucher_V2)
        
        Args:
            voucher_no: Voucher number
            print_type: 1=thermal, 2=laser A4 (default)
            output_path: Path to save PDF
            
        Returns:
            Dict with PDF data or file path
        """
        params = {
            "Voucher_No": voucher_no,
            "Print_Type": print_type,  # 1=thermal, 2=laser
            "Start_Position": 1,  # Position on A4 (1, 2, or 3)
            "Language": "GR"
        }
        
        result = self._make_request("ACS_Print_Voucher_V2", params)
        
        if result['success']:
            # Response contains PDF in ACSObjectOutput (not ACSValueOutput!)
            obj_output = result['data'].get('ACSObjectOutput', [])
            
            if obj_output and len(obj_output) > 0:
                # PDF is in format: {voucher_no: base64_pdf_data}
                pdf_data = obj_output[0]
                
                # Get the PDF (voucher_no is the key)
                pdf_base64 = pdf_data.get(voucher_no)
                
                if pdf_base64:
                    if output_path:
                        # Decode and save
                        pdf_bytes = base64.b64decode(pdf_base64)
                        with open(output_path, 'wb') as f:
                            f.write(pdf_bytes)
                        
                        return {
                            'success': True,
                            'file_path': output_path
                        }
                    else:
                        return {
                            'success': True,
                            'pdf_base64': pdf_base64
                        }
        
        return {
            'success': False,
            'error': 'Failed to get PDF'
        }
    
    def create_pickup_list(self, pickup_date: str = None, my_data: int = 0) -> Dict:
        """
        Create pickup list (MANDATORY - finalizes vouchers!)
        Documentation: Page 13 (ACS_Issue_Pickup_List)
        
        CRITICAL: Without this, voucher barcodes won't work!
        
        Args:
            pickup_date: Date in 'YYYY-MM-DD' format (default: today)
            my_data: 0=all users, 1=current user only
            
        Returns:
            Dict with PickupList_No
        """
        if not pickup_date:
            pickup_date = date.today().strftime('%Y-%m-%d')
        
        params = {
            "Pickup_Date": pickup_date,
            "MyData": my_data,
            "Language": "GR"
        }
        
        result = self._make_request("ACS_Issue_Pickup_List", params)
        
        if result['success']:
            output = result['data'].get('ACSValueOutput', [])
            
            if output and len(output) > 0:
                pickup_info = output[0]
                
                pickup_list_no = pickup_info.get('PickupList_No')
                unprinted = pickup_info.get('Unprinted_Found', 0)
                error_msg = pickup_info.get('Error_Message', '')
                
                if pickup_list_no:
                    return {
                        'success': True,
                        'pickup_list_no': pickup_list_no.strip(),
                        'unprinted_found': unprinted,
                        'message': 'Pickup list created successfully'
                    }
                elif error_msg:
                    # Check for unprinted vouchers
                    table_output = result['data'].get('ACSTableOutput', {})
                    unprinted_vouchers = table_output.get('Table_Data', [])
                    
                    return {
                        'success': False,
                        'error': error_msg,
                        'unprinted_vouchers': [
                            v.get('Unprinted_Vouchers') 
                            for v in unprinted_vouchers
                        ]
                    }
        
        return {
            'success': False,
            'error': 'Failed to create pickup list'
        }
    
    def print_pickup_list(self, mass_number: str, pickup_date: str = None,
                         output_path: str = None) -> Dict:
        """
        Print pickup list as PDF
        Documentation: Page 14 (ACS_Print_Pickup_List)
        
        Args:
            mass_number: PickupList_No from create_pickup_list
            pickup_date: Date in 'YYYY-MM-DD' format
            output_path: Path to save PDF
            
        Returns:
            Dict with PDF data
        """
        if not pickup_date:
            pickup_date = date.today().strftime('%Y-%m-%d')
        
        params = {
            "Mass_Number": mass_number,
            "Pickup_Date": pickup_date,
            "Language": "GR"
        }
        
        result = self._make_request("ACS_Print_Pickup_List", params)
        
        if result['success']:
            obj_output = result['data'].get('ACSObjectOutput', [])
            
            if obj_output:
                pdf_base64 = obj_output[0]
                
                if output_path:
                    pdf_bytes = base64.b64decode(pdf_base64)
                    with open(output_path, 'wb') as f:
                        f.write(pdf_bytes)
                    
                    return {
                        'success': True,
                        'file_path': output_path
                    }
                else:
                    return {
                        'success': True,
                        'pdf_base64': pdf_base64
                    }
        
        return {
            'success': False,
            'error': 'Failed to print pickup list'
        }
    
    def track_shipment_summary(self, voucher_no: str) -> Dict:
        """
        Get tracking summary (latest status)
        Documentation: Page 18-20 (ACS_Trackingsummary)
        
        Args:
            voucher_no: Voucher number to track
            
        Returns:
            Dict with tracking information
        """
        params = {
            "Voucher_No": voucher_no,
            "Language": "GR"
        }
        
        result = self._make_request("ACS_Trackingsummary", params)
        
        if result['success']:
            table_output = result['data'].get('ACSTableOutput', {})
            table_data = table_output.get('Table_Data', [])
            
            if table_data and len(table_data) > 0:
                tracking = table_data[0]
                
                return {
                    'success': True,
                    'voucher_no': tracking.get('voucher_no'),
                    'status': tracking.get('shipment_status'),
                    'delivery_flag': tracking.get('delivery_flag'),
                    'returned_flag': tracking.get('returned_flag'),
                    'delivery_date': tracking.get('delivery_date'),
                    'delivery_info': tracking.get('delivery_info'),
                    'recipient': tracking.get('recipient'),
                    'station_origin': tracking.get('acs_station_origin_descr'),
                    'station_destination': tracking.get('acs_station_destination_descr')
                }
        
        return {
            'success': False,
            'error': 'No tracking data available'
        }
    
    def delete_voucher(self, voucher_no: str) -> Dict:
        """
        Delete voucher (ONLY before pickup list created!)
        Documentation: Page 11 (ACS_Delete_Voucher)
        
        Args:
            voucher_no: Voucher number to delete
            
        Returns:
            Dict with deletion status
        """
        params = {
            "Voucher_No": voucher_no,
            "Language": "GR"
        }
        
        result = self._make_request("ACS_Delete_Voucher", params)
        
        if result['success']:
            output = result['data'].get('ACSValueOutput', [])
            
            if output and len(output) > 0:
                delete_info = output[0]
                error_msg = delete_info.get('Error_Message')
                
                if not error_msg:
                    return {
                        'success': True,
                        'message': 'Voucher deleted successfully'
                    }
                else:
                    return {
                        'success': False,
                        'error': error_msg
                    }
        
        return result
    
    def validate_address(self, address: str, address_id: str = None) -> Dict:
        """
        Validate Greek address
        Documentation: Page 24-25 (ACS_Address_Validation)
        
        Args:
            address: Full address string
            address_id: Optional reference ID
            
        Returns:
            Dict with validated address components
        """
        params = {
            "Address": address,
            "AddressID": address_id,
            "Language": "GR"
        }
        
        result = self._make_request("ACS_Address_Validation", params)
        
        if result['success']:
            output = result['data'].get('ACSValueOutput', [])
            
            if output and len(output) > 0:
                obj_output = output[0].get('ACSObjectOutput', [])
                
                if obj_output:
                    validated = obj_output[0]
                    
                    return {
                        'success': True,
                        'street': validated.get('Resolved_Street'),
                        'number': validated.get('Resolved_Street_Num'),
                        'zipcode': validated.get('Resolved_Zip'),
                        'area': validated.get('Resolved_Area'),
                        'station_id': validated.get('Resolved_Station_ID'),
                        'branch_id': validated.get('Resolved_Branch_ID'),
                        'latitude': validated.get('Resolved_Lat'),
                        'longitude': validated.get('Resolved_Long'),
                        'is_remote': validated.get('Resolved_As_Inaccesible_Area_With_Cost', 0) == 1
                    }
        
        return {
            'success': False,
            'error': 'Address validation failed'
        }
    
    def test_connection(self) -> bool:
        """
        Test API connection
        
        Returns:
            True if API is accessible
        """
        try:
            # Try validating a simple address
            result = self.validate_address("ΡΟΜΒΗΣ 25 17778")
            return result.get('success', False)
        except:
            return False


# ==================== UTILITY FUNCTIONS ====================

def format_phone(phone: str) -> str:
    """
    Format phone number for ACS
    Removes spaces, dashes, parentheses
    """
    return ''.join(filter(str.isdigit, str(phone)))


def validate_zipcode(zipcode: str) -> bool:
    """Validate Greek zipcode (exactly 5 digits)"""
    zipcode = str(zipcode).strip()
    return zipcode.isdigit() and len(zipcode) == 5


def split_address(full_address: str) -> tuple:
    """
    Split address into street and number
    
    Returns:
        (street, number)
    """
    import re
    
    # Try to extract number from end of address
    match = re.search(r'(.+?)\s+(\d+\w*)$', full_address.strip())
    
    if match:
        return match.group(1).strip(), match.group(2).strip()
    else:
        return full_address.strip(), ''


def calculate_volumetric_weight(length_cm: float, width_cm: float, 
                               height_cm: float) -> float:
    """
    Calculate volumetric weight
    Formula from documentation page 22: L×W×H / 5000
    
    Returns:
        Weight in kg
    """
    return (length_cm * width_cm * height_cm) / 5000