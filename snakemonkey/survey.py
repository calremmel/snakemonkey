import csv
import json
from dataclasses import dataclass

from tqdm import tqdm
import requests
from transformer import Transformer
from utils import clean_column, strip_tags

_INVESTIGATE = [
    "date_created",
    "date_modified",
    "response_id",
    "In what ZIP code is your home located? (enter 5-digit ZIP code; for example, 00544 or 94305)",
    "What is your age?",
    "How many COVID-19 vaccine doses have you received?",
    "Over the past month, on an average day, about how many people (including family members) have you had close contact (within 6 feet) with?",
    "For how many days after getting sick will you continue to practice these behaviors?",
    "Optional: would you like to hear more from COVID Near You? Submit your phone number to receive text message reminders to update your health status, get information on testing facilities, or learn about important news in your community. Message and data rates may apply, reply HELP for help or STOP to cancel. Message frequency may vary, but expect 4/month. Read our Terms & Conditions and Privacy Policy.",
    "What was your highest recorded temperature, in degrees Fahrenheit?",
]


@dataclass()
class Survey:
    token: str
    base_url: str
    headers: dict
    survey_id: int
    details: dict
    families: dict
    questions: dict
    answers: dict

    def get_survey_responses(self, page, status="completed"):
        """Gets a page of responses for Survey..

        Parameters
        ----------
        page : int
            Page of responses to retrieve.
        status : str
            Status of responses accepted. "completed" by default.

        Returns
        -------

        """
        endpoint = f"surveys/{self.survey_id}/responses/bulk"
        params = {"page": page, "per_page": 100}
        if status:
            params["status"] = status
        result = requests.get(
            url=f"{self.base_url}/{endpoint}",
            params=params,
            headers=self.headers,
        )
        return result.json()

    def get_all_survey_responses(self, status="completed"):
        """Gets all responses associated with Survey.

        Returns
        -------
        list of dict
            All responses associated with survey.
        status : str
            Status of responses accepted. "completed" by default.

        """
        all_responses = []
        more_surveys = True
        current_page = 1
        while more_surveys:
            print(f"Gathering page: {current_page}")
            responses = self.get_survey_responses(current_page, status)
            all_responses.append(responses)
            if "next" not in responses["links"].keys():
                self.responses = all_responses
                return
            current_page += 1

    def parse_survey(self):
        transform = Transformer(self.questions, self.answers)
        responses = [response for page in self.responses for response in page["data"]]
        records = []
        for response in tqdm(responses):
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
                            row |= transform.process_matrix(question)
                        if family == "multiple_choice":
                            row |= transform.process_multiple_choice(question)
                        if family == "single_choice":
                            row |= transform.process_single_choice(question)
                        if family == "open_ended":
                            row |= transform.process_open_ended(question)
                        if family == "datetime":
                            row |= transform.process_datetime(question)
            records.append(row)
        self.parsed_records = records

    def get_all_column_names(self):
        columns = []
        survey = self.details
        for page in survey["pages"]:
            for question in page["questions"]:
                if question.get("answers"):
                    question_text = strip_tags(question["headings"][0]["heading"])
                    if question["family"] == "single_choice":
                        columns.append(question_text)
                    elif question["family"] == "multiple_choice":
                        for key in question["answers"]:
                            if key == "other":
                                option = question["answers"][key]
                                col = " - ".join([question_text, option["text"]])
                                columns.append(col)
                            else:
                                for option in question["answers"][key]:
                                    col = " - ".join([question_text, option["text"]])
                                    columns.append(col)
                    elif question["family"] == "matrix":
                        for row in question["answers"]["rows"]:
                            col = " - ".join([question_text, row["text"]])
                            columns.append(col)
                    else:
                        for key in question["answers"].keys():
                            for option in question["answers"][key]:
                                col = " - ".join([question_text, option["text"]])
                                columns.append(col)
        columns = [clean_column(col) for col in columns]
        self.all_columns = _INVESTIGATE + columns
        return columns

    def to_csv(self, filename):
        if not self.all_columns:
            self.get_all_column_names()
        with open(filename, "w") as f:
            writer = csv.DictWriter(f, fieldnames=self.all_columns)
            writer.writeheader()
            for row in tqdm(self.parsed_records):
                writer.writerow(row)

    def to_jsonl(self, filename):
        with open(filename, "w") as f:
            for row in tqdm(self.parsed_records):
                f.write(json.dumps(row))