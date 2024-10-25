import requests
import json


ISSUE_URL = "https://api.github.com/repos/ubiquity-os/conversation-rewards/issues/5"
ISSUE_COMMENT_URL = "https://api.github.com/repos/ubiquity-os/conversation-rewards/issues/5/comments"

OLD_PROMPT_TEMPLATE = """
Instruction: 
    Go through all the comments first keep them in memory, then start with the following prompt

    OUTPUT FORMAT:
    {{ID: CONNECTION SCORE}} For Each record in the EVALUATING SECTION, based on the average value from the CONNECTION SCORE from ALL COMMENTS, TITLE and BODY, one for each comment under evaluation
    Global Context:
    Specification
    "{issue}"
    ALL COMMENTS:
    {all_comments}
    IMPORTANT CONTEXT:
    You have now seen all the comments made by other users, keeping the comments in mind think in what ways comments to be evaluated be connected. The comments that were related to the comment under evaluation might come after or before them in the list of all comments but they would be there in ALL COMMENTS. COULD BE BEFORE OR AFTER, you have diligently search through all the comments in ALL COMMENTS.
    START EVALUATING:
    {comments}
    POST EVALUATION:
    THE RESULT FROM THIS SHOULD BE ONLY THE SCORES BASED ON THE FLOATING POINT VALUE CONNECTING HOW CLOSE THE COMMENT IS FROM ALL COMMENTS AND TITLE AND BODY.

    Now Assign them scores a float value ranging from 0 to 1, where 0 is spam (lowest value), and 1 is something that's very relevant (Highest Value), here relevance should mean a variety of things, it could be a fix to the issue, it could be a bug in solution, it could a SPAM message, it could be comment, that on its own does not carry weight, but when CHECKED IN ALL COMMENTS, may be a crucial piece of information for debugging and solving the ticket. If YOU THINK ITS NOT RELATED to ALL COMMENTS or TITLE OR ISSUE SPEC, then give it a 0 SCORE.

    OUTPUT:
    RETURN ONLY A JSON with the ID and the connection score (FLOATING POINT VALUE) with ALL COMMENTS TITLE AND BODY for each comment under evaluation.  RETURN ONLY ONE CONNECTION SCORE VALUE for each comment. Total number of properties in your JSON response should equal exactly {comments_length}
"""
NEW_PROMPT_TEMPLATE = """
    Evaluate the relevance of GitHub comments to an issue. Provide a JSON object with comment IDs and their relevance scores.

Issue: {issue}

All comments:
{all_comments}

Comments to evaluate:
{comments}

Instructions:
1. Read all comments carefully, considering their context and content.
2. Evaluate each comment in the "Comments to evaluate" section.
3. Assign a relevance score from 0 to 1 for each comment:
   - 0: Not related (e.g., spam)
   - 1: Highly relevant (e.g., solutions, bug reports)
4. Consider:
   - Relation to the issue description
   - Connection to other comments
   - Contribution to issue resolution
5. Handle GitHub-flavored markdown:
   - Ignore text beginning with '>' as it references another comment
   - Distinguish between referenced text and the commenter's own words
   - Only evaluate the relevance of the commenter's original content
6. Return a JSON object: {{ID: score}}

Notes:
- Even minor details may be significant.
- Comments may reference earlier comments.
- The number of entries in the JSON response must equal {comments_length}.
"""
SKIP_COMMENT = ["/start","/stop","/wallet"]
SKIP_AUTHORS = ["ubiquibot[bot]","ubiquity","ubiquity-os-beta"]

def format_issue() -> str:
    issue_data = requests.get(
        ISSUE_URL
    )
    main_data = issue_data.json()
    issue_body = main_data["body"]
    return issue_body

def check_comment(comment):
    for exclude in SKIP_COMMENT:
        if comment.startswith(exclude):
            return True
    return False

def format_comment() -> list[dict]:
    comment_data = requests.get(
        ISSUE_COMMENT_URL
    )
    main_data = comment_data.json()
    all_comments = []
    for comment in main_data:
        if comment["user"]["login"] in SKIP_AUTHORS:
            continue
        if check_comment(comment["body"]):
            continue
        comment_dict = {
            "id": comment["id"],
            "comment": comment["body"],
            "author": comment["user"]["login"]
        }
        all_comments.append(comment_dict)
    return all_comments

def map_evaluation_comments(comment):
    return {
        "id": comment["id"],
        "comment": comment["comment"]
    }

def get_comment() -> tuple[dict, dict]:
    comment_data = format_comment()
    if len(comment_data) < 2:
        raise Exception(f"Comment length is too low. length: {len(comment_data)}")
    if len(comment_data) >= 3:
        evaluation_comment_length = round(len(comment_data) * 0.33)
        comments_length = len(comment_data) - evaluation_comment_length
    else:
        evaluation_comment_length = 1
        comments_length = 1
    comments = comment_data[:comments_length]
    evaluation_comments = comment_data[comments_length:]
    evaluation_comments = list(map(map_evaluation_comments, evaluation_comments))
    print(f"length all comments: {len(comments)}")
    print(f"length evaluation comments: {len(evaluation_comments)}")
    return (comments, evaluation_comments)

    


def generate_new_prompt_text(file_name: str = "new_prompt.txt", to_file: bool = True):
    print("New Prompt Start")
    issue = format_issue()
    comments, evaluation_comments = get_comment()
    comments_map = list(map(lambda x: f'{x["id"]} - {x["author"]}: \"{x["comment"]}\"', comments))
    evaluation_comments_map = list(map(lambda x: f'{x["id"]}: \"{x["comment"]}\" - ', evaluation_comments))
    new_text = NEW_PROMPT_TEMPLATE.format(
        issue = issue,
        comments = "\n".join(evaluation_comments_map),
        all_comments = "\n".join(comments_map),
        comments_length = len(evaluation_comments_map)
    )
    if to_file:
        with open(file_name,"w") as file:
            file.write(new_text)
    else:
        print(new_text)
    return new_text
            

def generate_old_prompt_text(file_name: str = "old_prompt.txt", to_file: bool = True):
    print("Old Prompt Start")
    issue = format_issue()
    comments, evaluation_comments = get_comment()
    old_text = OLD_PROMPT_TEMPLATE.format(
        issue = issue,
        comments = json.dumps(evaluation_comments, indent=2),
        all_comments = json.dumps(comments, indent=2),
        comments_length = len(evaluation_comments)
    )
    if to_file:
        with open(file_name,"w") as file:
            file.write(old_text)
    else:
        print(old_text)
    return old_text

if __name__ == "__main__":
    generate_old_prompt_text()
    generate_new_prompt_text()