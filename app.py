import streamlit as st
import requests
import base64
import datetime
import pandas as pd
import hmac

# Authentication function
def check_password():
    """Returns `True` if the user had the correct password."""

    def validate_credentials(username, password):
        # Compare with hashed passwords from secrets
        correct_usernames = st.secrets.get("auth", {}).get("usernames", {})
        
        if username in correct_usernames:
            # Get stored password hash
            stored_password = correct_usernames.get(username)
            # Verify password using hmac for comparison (to avoid timing attacks)
            return hmac.compare_digest(stored_password, password)
        
        return False

    # Check if authentication state already exists
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    
    # Return True if already authenticated
    if st.session_state.authenticated:
        return True

    # Create login form
    st.title("Welcome to CRM Deals")
    st.subheader("Please log in to continue")
    
    # Create input widgets
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    
    # Add login button
    if st.button("Login"):
        if validate_credentials(username, password):
            st.session_state.authenticated = True
            st.success("Login successful!")
            st.rerun()  # Rerun the app to refresh after login
        else:
            st.error("Invalid username or password")
            return False
    
    return False

# API configuration (moved to secrets)
def get_api_config():
    API_KEY = st.secrets.get("affinity", {}).get("api_key", "")
    BASE_URL = st.secrets.get("affinity", {}).get("base_url", "https://api.affinity.co")
    LIST_ID = st.secrets.get("affinity", {}).get("review_list_id", 247719)
    MASTER_DEALFLOW_LIST_ID = st.secrets.get("affinity", {}).get("master_list_id", 119553)
    
    return API_KEY, BASE_URL, LIST_ID, MASTER_DEALFLOW_LIST_ID

# Constants for person ID mapping (moved to a structured secret)
def get_person_id_mappings():
    # Get mapping from secrets
    name_to_id_mapping = st.secrets.get("mappings", {}).get("name_to_person_id", {})
    
    # If not found in secrets, use the original hardcoded mapping (for backward compatibility)
    if not name_to_id_mapping:
        name_to_id_mapping = {
            "Ari": "90412512",
            "Clara": "93680204",
            "David": "90412518",
            "Kristian": "90412276",
            "Mona": "93680252",
            "Shan": "209718589",
            "Pass": "96837197"
        }
    
    # Create reverse mapping
    person_id_to_name = {v: k for k, v in name_to_id_mapping.items()}
    
    return name_to_id_mapping, person_id_to_name

# Field mapping with ID and display name
def get_field_mappings():
    # Get from secrets
    field_map = st.secrets.get("mappings", {}).get("field_map", {})
    
    # If not found in secrets, use original mapping
    if not field_map:
        field_map = {
            "5060412": "User profile",
            "5047909": "Deal category",
            "5047891": "Reviewed",
            "4514989": "Date",
            "4514991": "Investors",
            "4514956": "Transition Owner",
            "5060345": "Stage",
            "4514990": "Last round type",
            "4627777": "Round size",
            "4627772": "Country",
            "4514974": "Summary"
        }
    
    # Convert string keys to integers if needed
    if all(isinstance(k, str) for k in field_map.keys()):
        field_map = {int(k): v for k, v in field_map.items()}
        
    return field_map

# Set up authentication
def get_auth_headers(api_key):
    auth = base64.b64encode(f":{api_key}".encode()).decode()
    return {
        "Authorization": f"Basic {auth}",
        "Content-Type": "application/json"
    }

# Function to convert person ID to name
def person_id_to_name(person_id, id_to_name_map):
    if not person_id:
        return "-"
    
    # Convert to string for comparison
    person_id_str = str(person_id)
    
    # Return name if found, otherwise return the ID
    return id_to_name_map.get(person_id_str, person_id_str)

# Function to fetch list entries with caching
@st.cache_data(ttl=3600)
def fetch_list_entries_cached(base_url, list_id, headers):
    url = f"{base_url}/lists/{list_id}/list-entries"
    params = {'page_size': 250}  # Get 250 entries at once
    
    response = requests.get(url, headers=headers, params=params)
    if response.status_code != 200:
        return []
    
    if isinstance(response.json(), dict) and 'list_entries' in response.json():
        data = response.json()
        return data.get('list_entries', [])
    else:
        return response.json()

# Function to fetch field values using list_entry_id with caching
@st.cache_data(ttl=3600)
def fetch_field_values_cached(base_url, entry_id, headers):
    field_values_url = f"{base_url}/field-values?list_entry_id={entry_id}"
    response = requests.get(field_values_url, headers=headers)
    if response.status_code != 200:
        return []
    return response.json()

# Function to check if entity is in Master Dealflow list
@st.cache_data(ttl=3600)
def check_master_dealflow(base_url, entity_id, master_list_id, headers):
    # Fetch the lists for this entity
    url = f"{base_url}/organizations/{entity_id}"
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        return "No"
    
    # Get list entries for the organization
    org_data = response.json()
    list_entries = org_data.get("list_entries", [])
    
    # Check if any list entry is for the Master Dealflow list
    for entry in list_entries:
        if entry.get("list_id") == master_list_id:
            return "Yes"
    
    return "No"

# Function to update a field value in Affinity
def update_field_value(base_url, entry_id, field_id, value, entity_id, headers):
    # If field value already exists, we need to find its ID first
    field_values = fetch_field_values_cached(base_url, entry_id, headers)
    field_value_id = None
    
    for fv in field_values:
        if fv.get("field_id") == field_id:
            field_value_id = fv.get("id")
            break
    
    if field_value_id:
        # Update existing field value
        url = f"{base_url}/field-values/{field_value_id}"
        data = {"value": value}
        response = requests.put(url, headers=headers, json=data)
    else:
        # Create new field value
        url = f"{base_url}/field-values"
        data = {
            "field_id": field_id,
            "entity_id": entity_id,
            "value": value,
            "list_entry_id": entry_id
        }
        response = requests.post(url, headers=headers, json=data)
    
    return response.status_code == 200 or response.status_code == 201

# Function to extract formatted field values from response
def extract_field_values(field_values_data, field_map):
    result = {}
    
    for field_value in field_values_data:
        field_id = field_value.get("field_id")
        if field_id in field_map:
            display_name = field_map[field_id]
            
            # Extract the appropriate value based on value type
            if "text_value" in field_value and field_value.get("text_value") is not None:
                result[display_name] = field_value.get("text_value")
            elif "number_value" in field_value and field_value.get("number_value") is not None:
                result[display_name] = field_value.get("number_value")
            elif "date_value" in field_value and field_value.get("date_value") is not None:
                result[display_name] = field_value.get("date_value")
            elif "value" in field_value:
                # Handle complex value types (like objects or dropdown options)
                result[display_name] = field_value.get("value")
    
    return result

# Function to format date to dd mmm yyyy
def format_date(date_str):
    if not date_str:
        return "-"
    try:
        date_obj = datetime.datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return date_obj.strftime("%d %b %Y")
    except:
        return date_str

# Function to format round size to $0.0m
def format_round_size(value):
    if not value:
        return "-"
    try:
        # Convert to float and then to millions with 1 decimal place
        value_float = float(value)
        value_millions = value_float / 1000000
        return f"${value_millions:.1f}m"
    except:
        return str(value)

# Main app
def main():
    # First, verify authentication
    if not check_password():
        # Don't proceed if not authenticated
        return
    
    # Get API configuration
    API_KEY, BASE_URL, LIST_ID, MASTER_DEALFLOW_LIST_ID = get_api_config()
    NAME_TO_PERSON_ID, PERSON_ID_TO_NAME = get_person_id_mappings()
    FIELD_MAP = get_field_mappings()
    
    # Set up headers
    headers = get_auth_headers(API_KEY)
    
    st.title("CRM Deals")
    
    # Create tabs for main view and summary
    tab1, tab2 = st.tabs(["Deals Queue", "Status Summary"])
    
    # Initialize session state
    if 'all_entries' not in st.session_state:
        st.session_state.all_entries = []
        st.session_state.current_index = 0
    
    # Initialize the track dropdown state
    if 'show_track_dropdown' not in st.session_state:
        st.session_state.show_track_dropdown = False
    
    # Add filters in a 2x2 grid within the first tab
    with tab1:
        col1, col2 = st.columns(2)
    
    # Filter for User profile - Added "UK / US" before "Other"
    with col1:
        user_profiles = ["All", "Ari", "Clara", "Kristian", "Mona", "UK / US", "Other"]
        selected_profile = st.selectbox("Filter by User Profile", user_profiles, 
                                      key="profile_filter", 
                                      on_change=lambda: setattr(st.session_state, 'current_index', 0))
    
    # Filter for Deal category
    with col2:
        categories = ["All", "Pre Seed/Accelerator", "Seed & Series A", "Series B+", "Exits", "Grants & Awards", "Other"]
        selected_category = st.selectbox("Filter by Category", categories, index=2,
                                        key="category_filter", 
                                        on_change=lambda: setattr(st.session_state, 'current_index', 0))
    
    # Second row of filters
    col3, col4 = st.columns(2)
    
    # Filter for Reviewed status
    with col3:
        review_statuses = ["Not Reviewed", "All"]
        selected_review_status = st.selectbox("Review Status", review_statuses,
                                             key="review_filter",
                                             on_change=lambda: setattr(st.session_state, 'current_index', 0))
    
    # Date filter
    with col4:
        date_ranges = ["Last 14 days", "Last 30 days", "Last 90 days", "All time"]
        selected_date_range = st.selectbox("Date Range", date_ranges, index=0,
                                          key="date_filter",
                                          on_change=lambda: setattr(st.session_state, 'current_index', 0))
    
    # Initialize loading status
    if 'loading_complete' not in st.session_state:
        st.session_state.loading_complete = False
    
    # Start loading entries if needed
    if len(st.session_state.all_entries) == 0:
        # Get entries
        entries = fetch_list_entries_cached(BASE_URL, LIST_ID, headers)
        
        # Initialize with at least one processed entry for immediate display
        if entries:
            entry = entries[0]
            entry_id = entry.get("id")
            entity_id = entry.get("entity_id")
            field_values = fetch_field_values_cached(BASE_URL, entry_id, headers)
            entry["formatted_values"] = extract_field_values(field_values, FIELD_MAP)
            tracking_status = check_master_dealflow(BASE_URL, entity_id, MASTER_DEALFLOW_LIST_ID, headers)
            entry["tracking_status"] = tracking_status
            
            # Store the first entry
            st.session_state.all_entries = [entry]
            
            # Set up background loading placeholder
            st.empty().info("Loading more entries in background...")
            
            # Process the rest of the entries in the background
            if len(entries) > 1:
                for i in range(1, len(entries)):
                    entry = entries[i]
                    entry_id = entry.get("id")
                    entity_id = entry.get("entity_id")
                    field_values = fetch_field_values_cached(BASE_URL, entry_id, headers)
                    entry["formatted_values"] = extract_field_values(field_values, FIELD_MAP)
                    tracking_status = check_master_dealflow(BASE_URL, entity_id, MASTER_DEALFLOW_LIST_ID, headers)
                    entry["tracking_status"] = tracking_status
                    st.session_state.all_entries.append(entry)
            
            st.session_state.loading_complete = True
    
    # Display status of loaded entries
    loading_message = "Loading entries in background..." if not st.session_state.loading_complete else f"Loaded {len(st.session_state.all_entries)} entries"
    st.caption(loading_message)
    
    # Apply filters to the stored entries
    filtered_entries = []
    
    # Calculate date threshold based on selection
    now = datetime.datetime.now()
    if selected_date_range == "Last 14 days":
        date_threshold = now - datetime.timedelta(days=14)
    elif selected_date_range == "Last 30 days":
        date_threshold = now - datetime.timedelta(days=30)
    elif selected_date_range == "Last 90 days":
        date_threshold = now - datetime.timedelta(days=90)
    else:  # All time
        date_threshold = None
    
    for entry in st.session_state.all_entries:
        formatted_values = entry.get("formatted_values", {})
        
        # Filter by user profile and category if not "All"
        include_entry = True
        
        # User profile filter
        if selected_profile != "All" and formatted_values.get("User profile") != selected_profile:
            include_entry = False
        
        # Deal category filter
        if selected_category != "All" and formatted_values.get("Deal category") != selected_category:
            include_entry = False
        
        # Review status filter
        if selected_review_status == "Not Reviewed" and formatted_values.get("Reviewed") is not None:
            include_entry = False
        
        # Date filter
        if date_threshold and "Date" in formatted_values:
            try:
                entry_date = datetime.datetime.fromisoformat(formatted_values["Date"].replace('Z', '+00:00'))
                if entry_date < date_threshold:
                    include_entry = False
            except (ValueError, TypeError, AttributeError):
                # If date parsing fails, keep the entry if we're filtering by date
                pass
        
        if include_entry:
            filtered_entries.append(entry)
    
    # Display queue status
    if filtered_entries:
        # Make sure current_index is in bounds
        if st.session_state.current_index >= len(filtered_entries):
            st.session_state.current_index = 0
            
        if st.session_state.current_index < 0:
            st.session_state.current_index = len(filtered_entries) - 1
            
        st.write(f"Showing entry {st.session_state.current_index + 1} of {len(filtered_entries)} matching entries")
    else:
        st.write("No entries match the current filters")
    
    # Status Summary Table in the second tab
    with tab2:
        st.subheader("Status Summary Table")
        
        # Calculate summary statistics by profile and category
        if st.session_state.all_entries:
            # Define categories and profiles for the table
            categories = ["Pre Seed/Accelerator", "Seed & Series A", "Series B+", "Exits", "Grants & Awards", "Other"]
            profiles = ["Ari", "Clara", "Kristian", "Mona", "UK / US", "Other"]
            
            # Create a nested dictionary to store counts
            summary_data = {}
            for profile in profiles:
                summary_data[profile] = {}
                for category in categories:
                    summary_data[profile][category] = {"reviewed": 0, "unreviewed": 0}
            
            # Add a row for totals
            summary_data["TOTAL"] = {}
            for category in categories:
                summary_data["TOTAL"][category] = {"reviewed": 0, "unreviewed": 0}
            
            # Count entries
            for entry in st.session_state.all_entries:
                formatted_values = entry.get("formatted_values", {})
                
                # Get the profile and category
                profile = formatted_values.get("User profile")
                category = formatted_values.get("Deal category")
                
                # If profile or category not in our list, count as "Other"
                if profile not in profiles:
                    profile = "Other"
                if category not in categories:
                    category = "Other"
                
                # Count as reviewed or unreviewed
                if formatted_values.get("Reviewed") is not None:
                    summary_data[profile][category]["reviewed"] += 1
                    # Add to totals
                    summary_data["TOTAL"][category]["reviewed"] += 1
                else:
                    summary_data[profile][category]["unreviewed"] += 1
                    # Add to totals
                    summary_data["TOTAL"][category]["unreviewed"] += 1
            
            # Create a DataFrame for the summary table
            
            # Initialize data for the DataFrame
            df_data = []
            
            # Fill the data
            for profile in profiles + ["TOTAL"]:
                row_data = {"User Profile": profile}
                
                # Add a column for row totals
                total_unreviewed = 0
                total_all = 0
                
                for category in categories:
                    unreviewed = summary_data[profile][category]["unreviewed"]
                    total = summary_data[profile][category]["unreviewed"] + summary_data[profile][category]["reviewed"]
                    row_data[category] = f"{unreviewed} of {total}" if total > 0 else "0 of 0"
                    
                    # Sum up for row totals
                    total_unreviewed += unreviewed
                    total_all += total
                
                # Add the totals column
                row_data["TOTAL"] = f"{total_unreviewed} of {total_all}" if total_all > 0 else "0 of 0"
                
                df_data.append(row_data)
            
            # Create the DataFrame
            df = pd.DataFrame(df_data)
            
            # Display the table with highlighting
            st.markdown("""
            <style>
            .dataframe td, .dataframe th {
                text-align: center !important;
                padding: 8px !important;
                border: 1px solid #ddd !important;
            }
            .dataframe th {
                background-color: #f2f2f2 !important;
                font-weight: bold !important;
            }
            .dataframe tr:last-child {
                background-color: #f2f2f2 !important;
                font-weight: bold !important;
            }
            .dataframe td:last-child {
                background-color: #f2f2f2 !important;
                font-weight: bold !important;
            }
            </style>
            """, unsafe_allow_html=True)
            
            # Display the DataFrame
            st.dataframe(df.set_index("User Profile"), use_container_width=True)
            
            # Add a caption explaining the table
            st.caption("Note: Each cell shows 'X of Y' where X = unreviewed deals and Y = total deals for each profile and category combination. The TOTAL row and column show aggregated totals.")
        else:
            st.info("Loading data... Please wait for the summary table to populate.")
    
    # Display current entry if any matches the filter
    if filtered_entries:
        # Get current entry
        current_entry = filtered_entries[st.session_state.current_index]
        entity = current_entry.get("entity", {})
        formatted_values = current_entry.get("formatted_values", {})
        
        # Display company name with domain as web icon hyperlink right next to it
        company_name = entity.get("name", "Unknown")
        company_domain = entity.get("domain", "")
        
        title_html = f"<h3 style='display:inline;margin-right:5px;'>{company_name}</h3>"
        if company_domain:
            title_html += f"<span style='margin-right:5px;'>{company_domain}</span><a href='https://{company_domain}' target='_blank' style='text-decoration:none;'>🌐</a>"
        st.markdown(title_html, unsafe_allow_html=True)
        
        # Format Stage (with fallback to Last round type)
        stage_value = formatted_values.get("Stage", None)
        if stage_value is None or stage_value == "-":
            stage_value = formatted_values.get("Last round type", "-")
        
        # Format Date
        date_value = formatted_values.get("Date", "-")
        
        # Create a two-column layout for Date and Stage
        date_stage_col1, date_stage_col2 = st.columns(2)
        with date_stage_col1:
            st.write(f"**Date:** {format_date(date_value)}")
        with date_stage_col2:
            st.write(f"**Stage:** {stage_value}")
        
        # Format Investors (whole row)
        investors_value = formatted_values.get("Investors", "-")
        st.write(f"**Investors:** {investors_value}")
        
        # Format Round size and Country
        round_size_value = formatted_values.get("Round size", "-")
        country_value = formatted_values.get("Country", "-")
        
        round_country_col1, round_country_col2 = st.columns(2)
        with round_country_col1:
            st.write(f"**Round size:** {format_round_size(round_size_value)}")
        with round_country_col2:
            st.write(f"**Country:** {country_value}")
        
        # Display Reviewed status and Tracking status
        reviewed_value = formatted_values.get("Reviewed", "-")
        tracking_status = current_entry.get("tracking_status", "No")
        
        review_tracking_col1, review_tracking_col2 = st.columns(2)
        with review_tracking_col1:
            if reviewed_value != "-":
                # Convert the ID to name
                reviewed_name = person_id_to_name(reviewed_value, PERSON_ID_TO_NAME)
                st.write(f"**Reviewed:** {reviewed_name}")
            else:
                st.write(f"**Reviewed:** {reviewed_value}")
        
        with review_tracking_col2:
            st.write(f"**Tracking:** {tracking_status}")
        
        # Format Summary
        summary_value = formatted_values.get("Summary", "-")
        st.write(f"**Summary:**")
        st.write(summary_value)
        
        # Set up variables used by all buttons
        user_profile = formatted_values.get("User profile")
        entity_id = current_entry.get("entity_id")
        entry_id = current_entry.get("id")
        
        # Create 2x2 button grid
        button_row1_col1, button_row1_col2 = st.columns(2)
        button_row2_col1, button_row2_col2 = st.columns(2)
        
        # Add CSS for consistent button styling
        st.markdown("""
        <style>
        div.stButton > button {
            width: 100%;
            height: 44px;
            white-space: nowrap;
        }
        
        /* Custom styles for the track dropdown */
        .track-dropdown {
            display: none;
            position: absolute;
            background-color: white;
            border: 1px solid rgba(49, 51, 63, 0.2);
            border-radius: 4px;
            z-index: 1000;
            width: calc(50% - 1rem);
            margin-top: 2px;
        }
        
        .track-dropdown.show {
            display: block;
        }
        </style>
        """, unsafe_allow_html=True)
        
        with button_row1_col1:
            # Previous button
            if len(filtered_entries) > 1:
                if st.button("← Previous", use_container_width=True):
                    st.session_state.current_index -= 1
                    st.rerun()
        
        with button_row1_col2:
            # Next button
            if st.button("Next →", use_container_width=True):
                st.session_state.current_index += 1
                st.rerun()
        
        with button_row2_col1:
            # Track button with callback to toggle dropdown
            if st.button("✅ Track", key="track_button", use_container_width=True):
                st.session_state.show_track_dropdown = not st.session_state.show_track_dropdown
                st.rerun()
                
            # Show dropdown if state is True
            if st.session_state.show_track_dropdown:
                # Create list of all users
                all_users = ["Ari", "Clara", "David", "Kristian", "Mona", "Shan"]
                
                with st.container():
                    for user in all_users:
                        if st.button(user, key=f"assign_{user}"):
                            # Update Transition Owner field (ID: 4514956)
                            success1 = update_field_value(BASE_URL, entry_id, 4514956, NAME_TO_PERSON_ID.get(user), entity_id, headers)
                            
                            # Update Reviewed field (ID: 5047891) 
                            success2 = update_field_value(BASE_URL, entry_id, 5047891, NAME_TO_PERSON_ID.get(user), entity_id, headers)
                            
                            # Create a list entry in the Master Dealflow list for this entity
                            master_list_url = f"{BASE_URL}/lists/{MASTER_DEALFLOW_LIST_ID}/list-entries"
                            master_list_data = {"entity_id": entity_id}
                            master_list_response = requests.post(master_list_url, headers=headers, json=master_list_data)
                            success3 = master_list_response.status_code == 200 or master_list_response.status_code == 201
                            
                            # If the entity was successfully added to the Master Dealflow list, update the field ID 2017295
                            success4 = True
                            if success3:
                                try:
                                    # Get the list entry ID from the response
                                    master_list_entry_data = master_list_response.json()
                                    master_list_entry_id = master_list_entry_data.get("id")
                                    
                                    # Use the same update_field_value function we use elsewhere
                                    success4 = update_field_value(BASE_URL, master_list_entry_id, 2017295, NAME_TO_PERSON_ID.get(user), entity_id, headers)
                                except Exception as e:
                                    success4 = False
                                    print(f"Error updating Master Dealflow field: {e}")
                            
                            # Hide the dropdown after selection
                            st.session_state.show_track_dropdown = False
                            
                            if success1 and success2 and success3:
                                # Move to the next entry regardless of field update success
                                if st.session_state.current_index < len(filtered_entries) - 1:
                                    st.session_state.current_index += 1
                                
                                # Show success/warning based on field update success
                                if success4:
                                    st.success(f"Successfully tracked to {user} and added to Master Dealflow")
                                else:
                                    st.warning(f"Tracked to {user}, but failed to update Master Dealflow field - user may already be assigned")
                                
                                # Refresh the page
                                st.rerun()
                            else:
                                error_message = "Failed to update fields"
                                if not success3:
                                    error_message += " or add to Master Dealflow"
                                st.error(error_message)
        
        with button_row2_col2:
            # Pass button
            if st.button("🗑️ Pass", use_container_width=True):
                # Update Reviewed field to "Pass"
                success = update_field_value(BASE_URL, entry_id, 5047891, NAME_TO_PERSON_ID.get("Pass"), entity_id, headers)
                
                if success:
                    # Move to the next entry
                    if st.session_state.current_index < len(filtered_entries) - 1:
                        st.session_state.current_index += 1
                    st.success("Marked as Pass")
                    # Refresh the fields
                    st.rerun()
                else:
                    st.error("Failed to update fields")
    else
