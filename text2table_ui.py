import streamlit as st
import pandas as pd
from io import BytesIO, StringIO

def add_empty_line(input_content, target_line):
    output = StringIO()
    for line in input_content.split('\n'):
        output.write(line + '\n')
        if line.strip() == target_line.strip():
            output.write('\n')
    return output.getvalue()

def add_line_breaker_to_content(content):
    # Split the content into sections based on the header delimiter
    sections = content.split('^PART-I - Details of Tax Deducted at Source^')
    
    if len(sections) < 2:
        raise ValueError("Expected header not found in the file")

    # Separate the header and the data sections
    header_section = sections[0]
    data_section = sections[1]

    # Find the header line in the data section
    lines = data_section.strip().split('\n')
    modified_lines = []
    header_found = False

    for line in lines:
        if not header_found and "Sr. No." in line:
            modified_lines.append(line)  # Add the header line
            modified_lines.append(' ' * 1)  # Add the line breaker after the header
            header_found = True
        else:
            modified_lines.append(line)

    # Combine the modified lines back into a single string
    modified_content = header_section + '^PART-I - Details of Tax Deducted at Source^' + '\n'.join(modified_lines)
    return modified_content

def read_data_from_content(content):
    # Process the content after adding line breaker
    sections = content.split('^PART-I - Details of Tax Deducted at Source^')[1].split('\n\n')

    all_data = []
    header = None

    for section in sections:
        lines = section.strip().split('\n')
        if not lines:
            continue

        deductor_info = lines[0].split('^')
        if len(deductor_info) < 3:
            continue

        deductor_number = deductor_info[0]
        deductor_name = deductor_info[1]
        deductor_tan = deductor_info[2]

        for line in lines[1:]:
            # Ignore the line breaker
            if line.strip() == '':
                continue
            
            cols = [col.strip() for col in line.split('^') if col.strip()]
            if not header and "Sr. No." in cols:
                header = cols
            elif header and cols and cols[0].isdigit() and len(cols) == len(header):
                all_data.append([deductor_number, deductor_name, deductor_tan] + cols)

    if not header:
        raise ValueError("Header not found in the file")

    full_header = ['Deductor Number', 'Name of Deductor', 'TAN of Deductor'] + header
    return full_header, all_data

def create_dataframe(header, data):
    df = pd.DataFrame(data, columns=header)

    numeric_columns = ['Amount Paid / Credited(Rs.)', 'Tax Deducted(Rs.)', 'TDS Deposited(Rs.)']

    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    return df

# Streamlit app
st.sidebar.title("File Input")
uploaded_file = st.sidebar.file_uploader("Upload a Text File", type=["txt"])

# Add a submit button
if st.sidebar.button("Submit") and uploaded_file is not None:
    try:
        # Read content from the uploaded file
        content = uploaded_file.getvalue().decode("utf-8")

        # Add empty line after the target line
        target_line = "Sr. No.^Name of Deductor^TAN of Deductor^^^^^Total Amount Paid / Credited(Rs.)^Total Tax Deducted(Rs.)^Total TDS Deposited(Rs.)"
        content_with_empty_line = add_empty_line(content, target_line)

        # Add a line breaker after the header
        modified_content = add_line_breaker_to_content(content_with_empty_line)

        # Process the modified content to extract data
        header, data = read_data_from_content(modified_content)

        # Create DataFrame
        df = create_dataframe(header, data)

        # Remove 'Deductor Number' and 'Sr. No.' columns if they exist
        df = df.drop(columns=['Deductor Number', 'Sr. No.'], errors='ignore')

        # Add a new 'Sr. No.' column starting from 1
        df.insert(0, 'Sr. No.', range(1, len(df) + 1))

        # Display updated DataFrame
        st.write("### Updated Extracted Data", df)

        # Download button for the DataFrame
        @st.cache_data
        def convert_df_to_excel(df):
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False)
            return output.getvalue()

        excel_data = convert_df_to_excel(df)
        st.sidebar.download_button(
            label="Download Excel",
            data=excel_data,
            file_name="Individual_data.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        st.error(f"An error occurred: {str(e)}")

elif uploaded_file is None:
    st.sidebar.write("Awaiting file upload...")