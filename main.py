import streamlit as st
import openai
import fitz
from selenium import webdriver
import pandas as pd
from selenium.webdriver.common.by import By
import os
from dotenv import load_dotenv
from langchain.llms import OpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

resume = st.file_uploader("Upload you resume in pdf format", type='pdf', accept_multiple_files=False,
                          label_visibility="visible")


def extract_text_from_pdf(pdf_bytes):
    pdf_text = ""
    pdf_document = fitz.open(stream=pdf_bytes.read(), filetype="pdf")

    for page_number in range(pdf_document.page_count):
        page = pdf_document.load_page(page_number)
        page_text = page.get_text("text")
        pdf_text += page_text + "\n"  # Add a newline after each page

    pdf_document.close()
    return pdf_text


def job_roles(content):
    llm = OpenAI(temperature=0)
    template = PromptTemplate(
        input_variables=['content'],
        template='From the given resume, {content} , give the job roles that the candidate can apply, by analysing '
                 'the projects, technical skills and experience'
                 'for as a comma separated string without any other words, just the job roles'
    )
    chain = LLMChain(llm=llm, prompt=template, output_key='job')
    response = chain({'content': content})
    return response['job']


if resume is not None and st.button("Resume Analysis"):

    text = extract_text_from_pdf(resume)
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    openai.api_key = api_key


    def resume_analyser(resume):
        llm = OpenAI(temperature=0.7)
        template = PromptTemplate(
            input_variables=['resume'],
            template='Analyze the provided {resume} for its content, focusing on key sections such as personal '
                     'details (name, email, LinkedIn), experience, skills, and projects. Evaluate the use of action '
                     'verbs and quantification in the resume to identify strengths, weaknesses, and improvement '
                     'suggestions. Compare the resume with an ideal one and provide concise insights for enhancement.'
        )
        chain = LLMChain(llm=llm, prompt=template, output_key='analysis')
        response = chain({'resume': resume})
        return response['analysis']


    analysis = resume_analyser(text)
    st.write(analysis)
    driver = webdriver.Chrome()
    driver.implicitly_wait(10)

    jobs = job_roles(text)

    # st.write(jobs)
    jobs_list = jobs.split(', ')
    base_url = 'https://www.linkedin.com/jobs/search?keywords={}&location=United%20States&geoId=103644278&trk=public_jobs_jobs-search-bar_search-submit&position=1&pageNum=0'
    driver.get(base_url)

    all_company = []
    all_position = []
    all_link = []

    for job in jobs_list:
        url = base_url.format(job)
        driver.get(url)
        companies = []
        positions = []
        linklist = []

        for i in range(20):
            try:
                company = driver.find_elements(By.CLASS_NAME, 'base-search-card__subtitle')[i].text
                position = driver.find_elements(By.CLASS_NAME, 'base-search-card__title')[i].text
                job_elem = driver.find_elements(By.CLASS_NAME, 'base-card__full-link')[i]
                link = job_elem.get_attribute('href')

                companies.append(company)
                positions.append(position)
                linklist.append(link)
            except IndexError:
                break

        all_company.extend(companies)
        all_position.extend(positions)
        all_link.extend(linklist)

    driver.quit()
    job_data = {'Company': all_company, 'Position': all_position, 'LinkedIn Link': all_link}
    jobs_df = pd.DataFrame(job_data)

    # Format the 'LinkedIn Link' column to display clickable links
    jobs_df['LinkedIn Link'] = jobs_df['LinkedIn Link'].apply(
        lambda link: f'<a href="{link}" target="_blank">LinkedIn Link</a>')

    st.write(jobs_df.to_html(escape=False, render_links=True), unsafe_allow_html=True)
