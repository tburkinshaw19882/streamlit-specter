def fetch_person_field_values(person_id):
    """Fetch field values for a specific person ID"""
    field_values_url = f"{BASE_URL}/field-values?person_id={person_id}"
    
    try:
        response = requests.get(field_values_url, headers=headers)
        if response.status_code != 200:
            st.error(f"Error fetching person field values: {response.status_code}")
            st.error(response.text)
            return None
        
        return response.json()
    except Exception as e:
        st.error(f"Exception while fetching person field values: {str(e)}")
        return Noneimport streamlit as st
import requests
import base64
import json

# API configuration
API_KEY = st.secrets.get("affinity", {}).get("api_key", "")
BASE_URL = "https://api.affinity.co"
LIST_ID = 259534  # The specific list ID you want to query

# Set up authentication
auth = base64.b64encode(f":{API_KEY}".encode()).decode()
headers = {
    "Authorization": f"Basic {auth}",
    "Content-Type": "application/json"
}

def main():
    st.title("Affinity API JSON Dumper")
    st.write(f"This app dumps JSON data for list ID: {LIST_ID}")
    
    # Button to fetch data
    if st.button("Fetch Data"):
        with st.spinner("Fetching list entries..."):
            # Fetch list entries (limited to 10)
            entries = fetch_list_entries()
            
            if not entries:
                st.error("Failed to fetch list entries or no entries found")
                return
            
            # Display the raw list entries JSON
            st.subheader("List Entries (First 10)")
            st.json(entries)
            
            # For each entry, fetch and display field values by entity_id
            st.subheader("Field Values for Each Entry (by entity_id)")
            
            for i, entry in enumerate(entries[:10]):
                entity_id = entry.get("entity_id")
                entry_id = entry.get("id")
                st.write(f"### Entry {i+1} (ID: {entry_id}, Entity ID: {entity_id})")
                
                with st.spinner(f"Fetching field values for entity ID {entity_id}..."):
                    field_values = fetch_entity_field_values(entity_id)
                    
                if field_values:
                    st.json(field_values)
                else:
                    st.write("No field values found or failed to fetch")
                
                st.markdown("---")

def fetch_list_entries():
    """Fetch the first 10 list entries for the specified list ID"""
    url = f"{BASE_URL}/lists/{LIST_ID}/list-entries"
    params = {'page_size': 10}  # Limit to 10 entries
    
    try:
        response = requests.get(url, headers=headers, params=params)
        if response.status_code != 200:
            st.error(f"Error fetching list entries: {response.status_code}")
            st.error(response.text)
            return []
        
        data = response.json()
        
        # Handle different response formats
        if isinstance(data, dict) and 'list_entries' in data:
            return data.get('list_entries', [])
        else:
            return data
    except Exception as e:
        st.error(f"Exception while fetching list entries: {str(e)}")
        return []

def fetch_entity_field_values(entity_id):
    """Fetch field values for a specific entity ID"""
    field_values_url = f"{BASE_URL}/field-values?entity_id={entity_id}"
    
    try:
        response = requests.get(field_values_url, headers=headers)
        if response.status_code != 200:
            st.error(f"Error fetching entity field values: {response.status_code}")
            st.error(response.text)
            return None
        
        return response.json()
    except Exception as e:
        st.error(f"Exception while fetching entity field values: {str(e)}")
        return None

if __name__ == "__main__":
    main()
