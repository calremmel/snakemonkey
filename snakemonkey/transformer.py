from dataclasses import dataclass


@dataclass()
class Transformer:
    questions: dict
    answers: dict

    def arrange_text_field(self, question_id, answer):
        question_text = " - ".join(
            [self.questions[question_id], self.answers[answer["other_id"]]]
        )
        answer_text = answer["text"]
        return question_text, answer_text

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
                question_text, answer_text = self.arrange_text_field(question_id, answer)
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
            # other_id denotes something like (Please Specify)
            if answer.get("other_id"):
                question_text, answer_text = self.arrange_text_field(question_id, answer)
                row[question_text] = answer_text
            elif len(answer) > 1:
                print(answer)
                raise ValueError("Answer has too many keys.")
            else:
                for key, value in answer.items():
                    if len(value) >= 9 and all([char.isdigit() for char in value]):
                        question_text = self.questions[question_id]
                        answer_text = self.answers[value]
                        row[question_text] = answer_text
                    else:
                        raise ValueError(answer)
                    
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
