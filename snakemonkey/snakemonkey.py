import json
from dataclasses import dataclass
from html.parser import HTMLParser
from io import StringIO

import requests


class HTMLRemover(HTMLParser):
    """Class for removing HTML tags from text."""

    def __init__(self):
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs = True
        self.text = StringIO()

    def handle_data(self, d):
        self.text.write(d)

    def get_data(self):
        return self.text.getvalue()


def strip_tags(text):
    """Removes HTML tags from text.

    Parameters
    ----------
    text : str
        Text containing HTML tags

    Returns
    -------
    str
        Text without HTML tags.

    """
    s = HTMLRemover()
    s.feed(text)
    return s.get_data()


@dataclass
class Client:
    """Client for interacting with SurveyMonkey API."""

    token: str
    base_url: str = "https://api.surveymonkey.com/v3"

    def __init__(self):
        self.answers = None
        self.questions = None
        self.families = None

    def __post_init__(self):
        self.headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.token}",
        }

    def get_surveys(self):
        endpoint = "surveys"
        result = requests.get(url=f"{self.base_url}/{endpoint}", headers=self.headers)
        return result.json()

    def get_single_survey(self, survey_id):
        """

        Parameters
        ----------
        survey_id : int
            Unique nine-digit ID for single survey.

        Returns
        -------

        """
        endpoint = f"surveys/{survey_id}"
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

    def get_survey_responses(self, survey_id, page, status="completed"):
        """Gets a page of responses for a single survey.

        Parameters
        ----------
        survey_id : int
            Unique nine-digit ID for single survey.
        page : int
            Page of responses to retrieve.
        status : str
            Status of responses accepted. "completed" by default.

        Returns
        -------

        """
        endpoint = f"surveys/{survey_id}/responses/bulk"
        params = {"page": page, "per_page": 100}
        if status:
            params["status"] = status
        result = requests.get(
            url=f"{self.base_url}/{endpoint}",
            params=params,
            headers=self.headers,
        )
        return result.json()

    def get_all_survey_responses(self, survey_id):
        """

        Parameters
        ----------
        survey_id : int
            Unique nine-digit ID for single survey.

        Returns
        -------
        list of dict
            All responses associated with survey.

        """
        all_responses = []
        more_surveys = True
        current_page = 1
        while more_surveys:
            print(f"Gathering page: {current_page}")
            responses = self.get_survey_responses(survey_id, current_page)
            all_responses.append(responses)
            if "next" not in responses["links"].keys():
                return all_responses
            current_page += 1

    def process_matrix(self, question):
        """Processes a question that is in matrix format.

        Parameters
        ----------
        question : dict
            A question in matrix format.

        Returns
        -------
        dict
            Processed question.

        """
        row = {}
        question_id = question["id"]
        for answer in question["answers"]:
            try:
                question_text = " - ".join(
                    [self.questions[question_id], self.answers[answer["row_id"]]]
                )
            except Exception as e:
                print(answer)
                print(e)
                raise ValueError
            answer_text = self.answers[answer["choice_id"]]
            row[question_text] = answer_text
        return row

    def process_multiple_choice(self, question):
        """Processes a multiple choice question.

        Parameters
        ----------
        question : dict
            A multiple choice question.

        Returns
        -------
        dict
            Processed question.

        """
        row = {}
        question_id = question["id"]
        for answer in question["answers"]:
            if answer.get("other_id"):
                question_text = " - ".join(
                    [self.questions[question_id], self.answers[answer["other_id"]]]
                )
                answer_text = answer["text"]
                row[question_text] = answer_text
            else:
                answer_text = self.answers[answer["choice_id"]]
                question_text = " - ".join([self.questions[question_id], answer_text])
                row[question_text] = answer_text
        return row

    def process_single_choice(self, question):
        """Processes simple question that accepts a single choice.

        Parameters
        ----------
        question : dict
            Single choice question

        Returns
        -------
        dict
            Processed question.

        """
        row = {}
        question_id = question["id"]
        for answer in question["answers"]:
            for value in answer.values():
                if len(value) == 9 and all([char.isdigit() for char in value]):
                    question_text = self.questions[question_id]
                    answer_text = self.answers[value]
                    row[question_text] = answer_text
                else:
                    question_text = self.questions[question_id]
                    answer_text = value
                    row[question_text] = answer_text
        return row

    def process_datetime(self, question):
        row = {}
        question_id = question["id"]
        answer = question["answers"][0]
        row[
            " - ".join([self.questions[question_id], self.answers[answer["row_id"]]])
        ] = answer["text"]
        return row

    def process_open_ended(self, question):
        row = {}
        question_id = question["id"]
        answer = question["answers"][0]
        row[self.questions[question_id]] = answer["text"]
        return row

    def get_survey_records(self, responses):
        records = []
        for response in responses["data"]:
            row = {
                "response_id": response["id"],
                "date_created": response["date_created"],
                "date_modified": response["date_modified"],
            }
            for page in response["pages"]:
                if page.get("questions"):
                    for question in page["questions"]:
                        question_id = question["id"]
                        family = self.families[question_id]
                        if family == "matrix":
                            row |= self.process_matrix(question)
                        if family == "multiple_choice":
                            row |= self.process_multiple_choice(question)
                        if family == "single_choice":
                            row |= self.process_single_choice(question)
                        if family == "open_ended":
                            row |= self.process_open_ended(question)
                        if family == "datetime":
                            row |= self.process_datetime(question)

            records.append(json.dumps(row))
        return records

    def set_survey_dictionary(self, survey_id):
        families = {}
        questions = {}
        answers = {}
        survey = self.get_survey_details(survey_id)
        for page in survey["pages"]:
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
        self.families = families
        self.questions = questions
        self.answers = answers

    def print_survey_details(self, survey_id):
        survey = self.get_survey_details(survey_id)
        for page in survey["pages"]:
            for question in page["questions"]:
                if question.get("answers"):
                    print(
                        question["id"], strip_tags(question["headings"][0]["heading"])
                    )
                    print(question["family"])
                    if question["family"] == "matrix":
                        print("ROWS & CHOICES")
                        for row in question["answers"]["rows"]:
                            for choice in question["answers"]["choices"]:
                                print(
                                    question["id"],
                                    row["id"],
                                    choice["id"],
                                    row["text"],
                                    choice["text"],
                                )
                    else:
                        if question["answers"].get("rows"):
                            print("ROWS")
                            for row in question["answers"]["rows"]:
                                print(question["id"], row["id"], row["text"].strip())
                        if question["answers"].get("choices"):
                            print("CHOICES")
                            for choice in question["answers"]["choices"]:
                                print(
                                    question["id"], choice["id"], choice["text"].strip()
                                )
                        if question["answers"].get("other"):
                            print("OTHER")
                            print(
                                question["id"],
                                question["answers"]["other"]["id"],
                                question["answers"]["other"]["text"].strip(),
                            )
                    print()
