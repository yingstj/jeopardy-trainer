"""
Jay's Jeopardy Trainer - Version without authentication
This is the same app but without login requirements
"""

# Copy the entire app.py content but comment out authentication lines
import sys
import subprocess

# Read the original app.py
with open('app.py', 'r') as f:
    lines = f.readlines()

# Find and comment out authentication-related lines
modified_lines = []
skip_next = 0

for i, line in enumerate(lines):
    # Skip import of auth_manager
    if 'from auth_manager import AuthManager' in line:
        modified_lines.append('# ' + line)
    # Skip auth initialization
    elif 'auth = AuthManager()' in line:
        modified_lines.append('# ' + line)
    # Skip authentication check block
    elif 'if not st.session_state.get' in line and 'authenticated' in line:
        modified_lines.append('# ' + line)
        skip_next = 2  # Skip the next 2 lines (auth.show_login_page() and st.stop())
    # Skip user menu
    elif 'auth.show_user_menu()' in line:
        modified_lines.append('# ' + line)
    # Skip auto-save
    elif 'auth.save_user_session()' in line:
        modified_lines.append('    # ' + line)
    elif skip_next > 0:
        modified_lines.append('# ' + line)
        skip_next -= 1
    else:
        modified_lines.append(line)

# Write modified content to temporary file
with open('app_temp.py', 'w') as f:
    f.writelines(modified_lines)

# Run the modified app
subprocess.run([sys.executable, '-m', 'streamlit', 'run', 'app_temp.py'])