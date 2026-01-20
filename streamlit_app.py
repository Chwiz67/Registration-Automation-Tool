import streamlit as st
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time

# Page config
st.set_page_config(
    page_title="Registration Automation",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Styling
st.markdown("""
    <style>
    body {
        background-color: #ffffff;
    }
    .main {
        padding: 2rem;
    }
    </style>
    """, unsafe_allow_html=True)

# Title
st.title("Registration Automation Tool")
st.markdown("Bulk registration from Excel files")

st.divider()

# Create columns for layout
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Registration URL")
    webinar_url = st.text_input(
        "Enter the registration page URL",
        placeholder="https://example.com/register/..."
    )
    
    st.subheader("Select File")
    uploaded_file = st.file_uploader("Choose an Excel file", type=["xlsx", "xls"])
    
    if uploaded_file:
        st.success(f"✓ File loaded: {uploaded_file.name}")
        
        # Preview data
        with st.expander("Preview data"):
            df = pd.read_excel(uploaded_file)
            st.dataframe(df.head(3), use_container_width=True)
            
            if len(df) > 3:
                st.caption(f"... and {len(df) - 3} more rows ({len(df)} total)")

with col2:
    st.subheader("Actions")
    start_button = st.button("Start Registration", type="primary", use_container_width=True)

st.divider()

st.subheader("Progress")

# Initialize session state for logs
if 'logs' not in st.session_state:
    st.session_state.logs = []

if 'running' not in st.session_state:
    st.session_state.running = False

# Placeholder for live logs
log_placeholder = st.empty()

def add_log(message):
    """Add message to logs"""
    st.session_state.logs.append(message)
    print(message)
    # Update display in real-time
    with log_placeholder.container():
        st.code('\n'.join(st.session_state.logs), language='')

def register_customers(df, webinar_url):
    """Main registration logic"""
    try:
        add_log("Loading Excel data...")
        add_log(f"✓ Loaded {len(df)} rows\n")
        
        add_log("Opening browser...")
        
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        
        # For Streamlit Cloud (Linux)
        options.binary_location = "/usr/bin/chromium"
        
        driver = webdriver.Chrome(
            service=Service("/usr/bin/chromedriver"),
            options=options
        )
        wait = WebDriverWait(driver, 6)
        
        success_count = 0
        failed_count = 0
        
        for index, row in df.iterrows():
            try:
                email = row.get('Your Email address', 'Unknown')
                first_name = row.get('First Name', 'Unknown')
                last_name = row.get('Last Name', 'Unknown')
                
                add_log(f"\n[{index + 1}/{len(df)}] Registering {first_name} {last_name}...")
                add_log(f"  Email: {email}")
                
                registration_success = False
                attempt = 0
                
                while attempt < 2 and not registration_success:
                    attempt += 1
                    if attempt > 1:
                        add_log(f"  → Retrying (attempt {attempt}/2)...")
                    
                    try:
                        driver.get(webinar_url)
                        
                        # Wait for form to be fully loaded and interactive
                        wait.until(EC.element_to_be_clickable((By.ID, "registrant.firstName")))
                        time.sleep(0.5)  # Extra wait for JS to initialize
                        add_log(f"  → Page loaded")
                        
                        driver.find_element(By.ID, "registrant.firstName").send_keys(str(first_name))
                        driver.find_element(By.ID, "registrant.lastName").send_keys(str(last_name))
                        driver.find_element(By.ID, "registrant.email").send_keys(str(email))
                        time.sleep(0.3)  # Let JS process basic fields
                        add_log(f"  → Filled: {first_name} {last_name} ({email})")
                        
                        driver.find_element(By.ID, "customQuestion0").send_keys(str(row.get("Your Organization Name", "")))
                        driver.find_element(By.ID, "customQuestion1").send_keys(str(row.get("Your Department", "")))
                        driver.find_element(By.ID, "customQuestion2").send_keys(str(row.get("Your Role/ Designation", "")))
                        driver.find_element(By.ID, "customQuestion4").send_keys(str(row.get("Your Point of Contact at Whatfix", "")))
                        driver.find_element(By.ID, "customQuestion5").send_keys(str(row.get("Name of the Base Application(s) on which you are using Whatfix", "")))
                        time.sleep(0.3)  # Let JS process custom fields
                        add_log(f"  → Filled custom fields")
                        
                        dropdown_value = str(row["Your Association with Whatfix"]).strip()
                        dropdown_trigger = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".custom-dropdown .dropdown-selected")))
                        dropdown_trigger.click()
                        
                        wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".custom-dropdown .dropdown-options li")))
                        time.sleep(0.2)  # Wait for dropdown animation
                        add_log(f"  → Dropdown opened")
                        
                        dropdown_options = driver.find_elements(By.CSS_SELECTOR, ".custom-dropdown .dropdown-options li")
                        selected = False
                        for option in dropdown_options:
                            if option.text.strip() == dropdown_value:
                                option.click()
                                selected = True
                                break
                        
                        if not selected:
                            add_log(f"  ✗ Dropdown value '{dropdown_value}' not found")
                            continue
                        
                        add_log(f"  → Selected: {dropdown_value}")
                        time.sleep(0.5)  # Let dropdown value register
                        
                        initial_url = driver.current_url
                        
                        # Try JavaScript submit first (more reliable)
                        try:
                            driver.execute_script("document.getElementById('registration.submit.button').click();")
                            add_log(f"  → Submit clicked (JavaScript)")
                        except:
                            # Fallback to regular click
                            submit_btn = wait.until(EC.element_to_be_clickable((By.ID, "registration.submit.button")))
                            submit_btn.click()
                            add_log(f"  → Submit clicked (Selenium)")
                        
                        # Wait for URL to change
                        time.sleep(2)  # Give page more time to redirect
                        current_url = driver.current_url
                        
                        if current_url != initial_url:
                            add_log(f"  ✓ URL changed to: {current_url}")
                            add_log(f"  ✓ REGISTRATION COMPLETE")
                            registration_success = True
                            success_count += 1
                        else:
                            add_log(f"  ✗ URL did not change (attempt {attempt}/2)")
                    
                    except Exception as e:
                        add_log(f"  ✗ Error (attempt {attempt}/2): {str(e)}")
                
                if not registration_success:
                    add_log(f"  ✗ FAILED after 2 attempts")
                    failed_count += 1
                
            except Exception as e:
                add_log(f"  ✗ FAILED: {str(e)}")
                failed_count += 1
        
        driver.quit()
        
        add_log(f"\n{'='*50}")
        add_log(f"REGISTRATION COMPLETE")
        add_log(f"✓ Successful: {success_count}")
        add_log(f"✗ Failed: {failed_count}")
        add_log(f"{'='*50}")
        
        return success_count, failed_count
        
    except Exception as e:
        add_log(f"\n✗ ERROR: {str(e)}")
        return 0, len(df)
    
    finally:
        st.session_state.running = False

# Handle start button
if start_button:
    if not uploaded_file:
        st.error("Please upload an Excel file first")
    elif not webinar_url or not webinar_url.startswith('http'):
        st.error("Please enter a valid URL")
    else:
        st.session_state.running = True
        st.session_state.logs = []
        
        df = pd.read_excel(uploaded_file)
        
        # Run registration (logs update in real-time via add_log)
        success, failed = register_customers(df, webinar_url)
        
        # Display final metrics
        st.divider()
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Successful", success)
        with col2:
            st.metric("Failed", failed)
        with col3:
            st.metric("Total", success + failed)
