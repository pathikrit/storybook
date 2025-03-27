import streamlit as st

if __name__ == "main":
    st.title("Story Generator")

    who = st.text_input("Who:", "3-year old boy named Aidan")
    prompt = st.text_input("Prompt:", "colorful bison and a monster truck")
    bedtime = st.checkbox("Bedtime")

    if st.button("Generate Story"):
        st.write("Story generation logic goes here!")
