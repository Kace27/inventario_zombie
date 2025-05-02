import requests
import json
import csv
import io
import os
import sys
from datetime import datetime

# Configuration
BASE_URL = 'http://127.0.0.1:5000/api'  # Flask default address
TEST_DATA_DIR = 'test_data'

def create_test_data_dir():
    """Create test data directory if it doesn't exist"""
    if not os.path.exists(TEST_DATA_DIR):
        os.makedirs(TEST_DATA_DIR)
        print(f"Created directory: {TEST_DATA_DIR}")

def create_test_sales_csv():
    """Create a test CSV file with sales data"""
    filename = os.path.join(TEST_DATA_DIR, 'test_sales.csv')
    
    # Sample sales data
    sales_data = [
        {
            'fecha': datetime.now().strftime('%Y-%m-%d'),
            'hora': datetime.now().strftime('%H:%M:%S'),
            'ticket': 'T-001',
            'empleado': 'Test Employee',
            'mesa': 'Table 1',
            'comensales': '2',
            'articulo': 'Test Product',
            'categoria': 'Test Category',
            'subcategoria': 'Test Subcategory',
            'precio_unitario': '10.50',
            'articulos_vendidos': '2',
            'iva': '1.68',
            'propina': '2.10',
            'total': '24.78'
        },
        {
            'fecha': datetime.now().strftime('%Y-%m-%d'),
            'hora': datetime.now().strftime('%H:%M:%S'),
            'ticket': 'T-002',
            'empleado': 'Test Employee',
            'mesa': 'Table 2',
            'comensales': '4',
            'articulo': 'Another Product',
            'categoria': 'Test Category',
            'subcategoria': 'Test Subcategory',
            'precio_unitario': '8.75',
            'articulos_vendidos': '4',
            'iva': '2.80',
            'propina': '3.50',
            'total': '41.30'
        }
    ]
    
    # Write to CSV
    with open(filename, 'w', newline='') as csvfile:
        fieldnames = sales_data[0].keys()
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        writer.writerows(sales_data)
    
    print(f"Created test sales CSV file: {filename}")
    return filename

def test_sales_import(csv_file):
    """Test the sales import API"""
    print("\n----- Testing Sales Import API -----")
    
    endpoint = f"{BASE_URL}/ventas/importar"
    
    # Create test files dict with open file
    with open(csv_file, 'rb') as f:
        files = {'file': (os.path.basename(csv_file), f, 'text/csv')}
        
        # Send POST request to import sales
        try:
            response = requests.post(endpoint, files=files)
            
            # Print response
            print(f"Status Code: {response.status_code}")
            print(f"Response: {json.dumps(response.json(), indent=2)}")
            
            if response.status_code == 200 and response.json().get('success'):
                print("✅ Sales import test PASSED")
                return True
            else:
                print("❌ Sales import test FAILED")
                return False
        
        except Exception as e:
            print(f"❌ Sales import test ERROR: {str(e)}")
            return False

def test_get_sales():
    """Test the GET sales API"""
    print("\n----- Testing Get Sales API -----")
    
    endpoint = f"{BASE_URL}/ventas"
    
    try:
        response = requests.get(endpoint)
        
        # Print response
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2) if response.text else 'No content'}")
        
        if response.status_code == 200 and response.json().get('success'):
            print("✅ Get sales test PASSED")
            return True
        else:
            print("❌ Get sales test FAILED")
            return False
    
    except Exception as e:
        print(f"❌ Get sales test ERROR: {str(e)}")
        return False

def get_test_ingredient_id():
    """Get a valid ingredient ID for testing"""
    endpoint = f"{BASE_URL}/ingredientes"
    
    try:
        response = requests.get(endpoint)
        print("\n----- Checking Available Ingredients -----")
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            response_data = response.json()
            print(f"Success: {response_data.get('success', False)}")
            
            if response_data.get('success'):
                ingredientes = response_data.get('data', [])
                print(f"Found {len(ingredientes)} ingredients")
                
                if ingredientes and len(ingredientes) > 0:
                    # Print first few ingredients for debugging
                    for i, ing in enumerate(ingredientes[:3]):
                        if isinstance(ing, dict):
                            print(f"Ingredient {i+1}: ID={ing.get('id')}, Name={ing.get('nombre')}")
                        else:
                            print(f"Ingredient {i+1} is not a dictionary: {ing}")
                    
                    # Return the first ingredient ID
                    if isinstance(ingredientes[0], dict) and 'id' in ingredientes[0]:
                        return ingredientes[0]['id']
                    else:
                        print(f"⚠️ First ingredient doesn't have an ID field: {ingredientes[0]}")
                else:
                    print("⚠️ No ingredients found, creating a test ingredient")
                    # Create a test ingredient
                    create_response = requests.post(
                        f"{BASE_URL}/ingredientes", 
                        json={
                            "nombre": f"Test Ingredient {datetime.now().strftime('%Y%m%d%H%M%S')}",
                            "unidad_medida": "kg",
                            "precio_compra": 10.0,
                            "cantidad_actual": 100.0,
                            "stock_minimo": 10.0
                        }
                    )
                    
                    if create_response.status_code == 200 and create_response.json().get('success'):
                        print(f"✅ Created test ingredient with ID: {create_response.json().get('data', {}).get('id')}")
                        return create_response.json().get('data', {}).get('id')
                    else:
                        print(f"❌ Failed to create ingredient: {create_response.text}")
            else:
                print(f"Error in response: {response_data.get('error', 'Unknown error')}")
        else:
            print(f"Error status code: {response.status_code}")
            print(f"Response text: {response.text}")
    
    except Exception as e:
        print(f"❌ Exception when getting ingredients: {str(e)}")
        # Print response details for debugging
        try:
            if response and hasattr(response, 'text'):
                print(f"Response text: {response.text[:200]}...")
        except:
            pass
    
    # Direct database method as a last resort
    print("⚠️ Attempting to create a test ingredient directly")
    try:
        create_response = requests.post(
            f"{BASE_URL}/ingredientes", 
            json={
                "nombre": f"Test Ingredient {datetime.now().strftime('%Y%m%d%H%M%S')}",
                "unidad_medida": "kg",
                "precio_compra": 10.0,
                "cantidad_actual": 100.0,
                "stock_minimo": 10.0
            }
        )
        
        print(f"Status Code: {create_response.status_code}")
        
        if create_response.status_code == 200:
            response_data = create_response.json()
            if response_data.get('success'):
                new_id = response_data.get('data', {}).get('id')
                if new_id:
                    print(f"✅ Successfully created ingredient with ID: {new_id}")
                    return new_id
                else:
                    print(f"❌ Created ingredient but no ID returned: {response_data}")
            else:
                print(f"❌ Failed to create ingredient: {response_data.get('error', 'Unknown error')}")
        else:
            print(f"❌ Error creating ingredient: {create_response.status_code}")
            if hasattr(create_response, 'text'):
                print(f"Response text: {create_response.text[:200]}...")
    except Exception as e:
        print(f"❌ Exception creating ingredient: {str(e)}")
    
    print("❌ All attempts to get/create ingredient failed")
    return None

def test_create_reception():
    """Test the create reception API"""
    print("\n----- Testing Create Reception API -----")
    
    endpoint = f"{BASE_URL}/recepciones"
    
    # First try ingredient ID 1 which should exist after running populate_test_data.py
    ingrediente_id = 1
    print(f"Using ingredient ID: {ingrediente_id} for reception test")
    
    # Data for the reception
    data = {
        "ingrediente_id": ingrediente_id,
        "cantidad_recibida": 10.5,
        "notas": "Test reception from API test script"
    }
    
    try:
        # Send POST request to create reception
        response = requests.post(endpoint, json=data)
        
        # Print response
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2) if response.text else 'No content'}")
        
        if response.status_code == 200 and response.json().get('success'):
            print("✅ Create reception test PASSED")
            return response.json().get('data', {}).get('id')
        else:
            print("❌ Create reception test FAILED")
            print("Falling back to ingredient lookup...")
            
            # Try to get any valid ingredient as fallback
            try:
                get_resp = requests.get(f"{BASE_URL}/ingredientes")
                if get_resp.status_code == 200 and get_resp.json().get('success'):
                    ingredientes = get_resp.json().get('data', [])
                    if ingredientes and len(ingredientes) > 0:
                        if isinstance(ingredientes[0], dict) and 'id' in ingredientes[0]:
                            ingrediente_id = ingredientes[0]['id']
                            print(f"Using ingredient ID from API: {ingrediente_id}")
                            
                            # Try again with the new ID
                            data["ingrediente_id"] = ingrediente_id
                            response = requests.post(endpoint, json=data)
                            print(f"Status Code: {response.status_code}")
                            print(f"Response: {json.dumps(response.json(), indent=2) if response.text else 'No content'}")
                            
                            if response.status_code == 200 and response.json().get('success'):
                                print("✅ Create reception test PASSED on second attempt")
                                return response.json().get('data', {}).get('id')
                            else:
                                print("❌ Create reception test FAILED on second attempt")
            except Exception as e:
                print(f"❌ Error in fallback attempt: {str(e)}")
            
            return None
    
    except Exception as e:
        print(f"❌ Create reception test ERROR: {str(e)}")
        return None

def test_get_receptions():
    """Test the GET receptions API"""
    print("\n----- Testing Get Receptions API -----")
    
    endpoint = f"{BASE_URL}/recepciones"
    
    try:
        response = requests.get(endpoint)
        
        # Print response
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2) if response.text else 'No content'}")
        
        if response.status_code == 200 and response.json().get('success'):
            print("✅ Get receptions test PASSED")
            return True
        else:
            print("❌ Get receptions test FAILED")
            return False
    
    except Exception as e:
        print(f"❌ Get receptions test ERROR: {str(e)}")
        return False

def test_get_reception_by_id(reception_id):
    """Test the GET reception by ID API"""
    print("\n----- Testing Get Reception by ID API -----")
    
    if not reception_id:
        print("⚠️ Skipping test: No reception ID available")
        return False
    
    endpoint = f"{BASE_URL}/recepciones/{reception_id}"
    
    try:
        response = requests.get(endpoint)
        
        # Print response
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2) if response.text else 'No content'}")
        
        if response.status_code == 200 and response.json().get('success'):
            print("✅ Get reception by ID test PASSED")
            return True
        else:
            print("❌ Get reception by ID test FAILED")
            return False
    
    except Exception as e:
        print(f"❌ Get reception by ID test ERROR: {str(e)}")
        return False

def main():
    """Main test function"""
    print("===== Phase 4 API Test Script =====")
    print(f"Base URL: {BASE_URL}")
    
    # Make sure test data directory exists
    create_test_data_dir()
    
    # Create test sales CSV
    csv_file = create_test_sales_csv()
    
    # Test sales import
    test_sales_import(csv_file)
    
    # Test get sales
    test_get_sales()
    
    # Test create reception
    reception_id = test_create_reception()
    
    # Test get receptions
    test_get_receptions()
    
    # Test get reception by ID
    test_get_reception_by_id(reception_id)
    
    print("\n===== Phase 4 Tests Complete =====")

if __name__ == "__main__":
    main() 