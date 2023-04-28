from dataclasses import dataclass

import requests
from snakemonkey.survey import Survey
from snakemonkey.utils import clean_column, strip_tags
from datetime import datetime

from tabulate import tabulate


def reformat_surveys(surveys):
    parsed_survey_list = []
    for s in surveys["data"]:
        if "[" in s["nickname"]:
            date_raw = s["nickname"].split("[")[1].replace("]", "")
            dmy = date_raw.split(".")
            dt = datetime(int("20" + dmy[2]), int(dmy[0]), int(dmy[1]))
            iso_date = dt.strftime("%Y-%m-%d")
            s["date"] = iso_date
        else:
            s["date"] = "NA"
        if "title" in s.keys():
            s.pop("title", None)
        parsed_survey_list.append(s)
    sorted_surveys = sorted(parsed_survey_list, key=lambda x: x["date"], reverse=True)
    return sorted_surveys


@dataclass
class Client:
    """Client for interacting with SurveyMonkey API."""

    token: str
    base_url: str = "https://api.surveymonkey.com/v3"

    def __post_init__(self):
        self.headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.token}",
        }

    def get_surveys(self, fmt="records"):
        endpoint = "surveys"
        result = requests.get(url=f"{self.base_url}/{endpoint}", headers=self.headers)
        result_dict = result.json()
        if fmt == "records":
            return result_dict
        if fmt == "table":
            surveys = reformat_surveys(result_dict)
            print(tabulate(surveys, headers="keys"))

    def get_survey_details(self, survey_id):
        """Gets the details object for a single survey.

        Parameters
        ----------
        survey_id : int
            Unique nine-digit ID for single survey.

        Returns
        -------

        """
        endpoint = f"surveys/{survey_id}/details"
        result = requests.get(url=f"{self.base_url}/{endpoint}", headers=self.headers)
        return result.json()

    def get_survey(self, survey_id):
        families = {}
        questions = {}
        answers = {}
        details = self.get_survey_details(survey_id)
        try:
            for page in details["pages"]:
                for question in page["questions"]:
                    questions[question["id"]] = strip_tags(
                        question["headings"][0]["heading"]
                    )
                    families[question["id"]] = question["family"]
                    if question.get("answers"):
                        if question["answers"].get("rows"):
                            for row in question["answers"]["rows"]:
                                answers[row["id"]] = row["text"].strip()
                        if question["answers"].get("choices"):
                            for choice in question["answers"]["choices"]:
                                answers[choice["id"]] = choice["text"].strip()
                        if question["answers"].get("other"):
                            answers[question["answers"]["other"]["id"]] = question[
                                "answers"
                            ]["other"]["text"].strip()
        except Exception as e:
            print(e)
            print(details)
            raise e
        cleaned_families = {k: clean_column(v) for k, v in families.items()}
        cleaned_questions = {k: clean_column(v) for k, v in questions.items()}
        cleaned_answers = {k: clean_column(v) for k, v in answers.items()}
        return Survey(
            self.token,
            self.base_url,
            self.headers,
            survey_id,
            details,
            cleaned_families,
            cleaned_questions,
            cleaned_answers,
        )
