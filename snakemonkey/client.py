from dataclasses import dataclass

import requests
from survey import Survey
from utils import clean_column, strip_tags


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

    def get_surveys(self):
        endpoint = "surveys"
        result = requests.get(url=f"{self.base_url}/{endpoint}", headers=self.headers)
        return result.json()

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
