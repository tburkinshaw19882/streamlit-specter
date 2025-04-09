import streamlit as st
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
            
            # For each entry, fetch and display organization data
            st.subheader("Organization Data for Each Entry")
            
            for i, entry in enumerate(entries[:10]):
                entity_id = entry.get("entity_id")
                entry_id = entry.get("id")
                st.write(f"### Entry {i+1} (ID: {entry_id}, Organization ID: {entity_id})")
                
                with st.spinner(f"Fetching organization data for entry {i+1}..."):
                    org_data = fetch_organization_data(entity_id)
                    
                if org_data:
                    st.json(org_data)
                else:
                    st.write("No organization data found or failed to fetch")
                
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

def fetch_organization_data(entity_id):
    """Fetch organization data for a specific entity ID"""
    org_url = f"{BASE_URL}/organizations/{entity_id}"
    
    try:
        response = requests.get(org_url, headers=headers)
        if response.status_code != 200:
            st.error(f"Error fetching organization data: {response.status_code}")
            st.error(response.text)
            return None
        
        return response.json()
    except Exception as e:
        st.error(f"Exception while fetching organization data: {str(e)}")
        return None

if __name__ == "__main__":
    main()
