"""
In this file we will execute the evaluation metrics for each agent using the
DeepEval evaluation framework

Each agent is evaluated individually

It is evaluated based on faithfullnes,grounded,correctivieness parameters for explainer agent

For this evaluation testing we will create the sample initial  State and also sample Roadmap
object, to pass as input to each individual agent

"""

import os
import json
from pathlib import Path

import pytest

from dotenv import load_dotenv

from graph.Flow_State import RoadMap,AgentState,initial_state,Topic
from agents.Topics_Explainer_Agent import Topic_Explainer_Agent_Node
from langchain_core.messages import AIMessage
#LLM Model for DeepEval, DeepEval by default uses the OpenAI LLMs
# So here we are using the same OpenAI LLMs

load_dotenv()

def run_explainer(topic_title: str ,topic_description : str,session_id:str):

    #set the initial state
    state            = initial_state(f"Learn {topic_title}", session_id)

    state["roadmap"] = RoadMap(goal=f"Learn {topic_title}",
                      total_estimated_weeks=2,
                      total_required_hours_per_week=5,
                      topics=[Topic(topic_title, topic_description, 60)])

    explainer_output = Topic_Explainer_Agent_Node(state)

    for msg in reversed(explainer_output.get("messages", [])):
        if (isinstance(msg, AIMessage) and msg.content
                and not getattr(msg, "tool_calls", None)):
            return str(msg.content)

    return ""


@pytest.mark.eval
class TestExplainerAgentQuality:

    FAITHFULNESS_THRESHOLD  = 0.6
    RELEVANCY_THRESHOLD     = 0.6

    @pytest.fixture(autouse=True)
    def setup(self,closure_notes_content):
        self.context_retrival = [closure_notes_content]

        #First get the output from the Topics Explainer Agent
        # Inputs it needs is:
        #       -> state["RoadMap"] , state["session_id"]
        # Outputs it writes is:
        #       -> state["messages"]

        print("\n[TestExplainerAgentQuality] Running Explainer for topic...")
        self.explanation = run_explainer(
            topic_title=" NLP Field",
            topic_description="Understand how NLP field works",
            session_id="eval-test-002",
        )

        if not self.explanation:
            pytest.skip("Explainer returned empty output")

        print(f"[TestExplainerAgentQuality] Explanation length: {len(self.explanation)} chars")


    def test_explainer_agent_faithfulness_to_source_notes(self):

        """
        Check the faithfullness of the explanation provided by the explainer agent
        """
        
        try:
            from deepeval import evaluate
            from deepeval.test_case import LLMTestCase
            from deepeval.metrics import FaithfulnessMetric
        except ImportError:
            pytest.skip("deepeval is not installed")   
        

        test_case = LLMTestCase(
            input="Explain NLP Field",
            actual_output=self.explanation,
            retrieval_context=self.context_retrival,
        )

        metric = FaithfulnessMetric(
            model="gpt-4o-mini",
            threshold=self.FAITHFULNESS_THRESHOLD,
            include_reason=True,
        )

        metric.measure(test_case)

        print(f"\n[Faithfulness] Score: {metric.score:.3f} "
              f"(threshold: {self.FAITHFULNESS_THRESHOLD})")
        if hasattr(metric, "reason") and metric.reason:
            print(f"[Faithfulness] Reason: {metric.reason}")

        assert metric.score >= self.FAITHFULNESS_THRESHOLD, (
            f"Faithfulness score {metric.score:.3f} below threshold "
            f"{self.FAITHFULNESS_THRESHOLD}.\n"
            "The explanation may contain hallucinated facts not in the notes.\n"
            f"Reason: {getattr(metric, 'reason', 'not available')}"
        )

    def test_explainer_agent_relevance_to_topic(self):

        """
        Check whether the explanation produced by explainer agent is more relevant to the asked topic
        or it wandered outside the topic and explaination some hallucination data
        """

        from deepeval.test_case import LLMTestCase
        from deepeval.metrics import AnswerRelevancyMetric

        relevance_testcase =  LLMTestCase( input="Explain NLP techniques, what they are and why they matter",
            actual_output=self.explanation,) 

        relevance_metric = AnswerRelevancyMetric(model="gpt-4o-mini",
                                               threshold=self.RELEVANCY_THRESHOLD,
                                               include_reason=True)  

        relevance_metric.measure(relevance_testcase)

        print(f"\n[Relevancy] Score: {relevance_metric.score:.3f} "
              f"(threshold: {self.RELEVANCY_THRESHOLD})")

        assert relevance_metric.score >= self.RELEVANCY_THRESHOLD, (
            f"Relevancy score {relevance_metric.score:.3f} below threshold "
            f"{self.RELEVANCY_THRESHOLD}.\n"
            "The explanation may have drifted from the topic."
        )

@pytest.mark.evalquiz
class TestQuizGeneratorAgentQuality():
    """
    This test cases will evaluate the quality of the questions being generated by this agent
    It will check whether generated questions were concept oriented or just straight forward
    question and based on this it will evalute the Quality of the question
    """

    QUESTION_QUALITY_THRESHOLD = 0.8
    
    def test_quality_of_generated_questions(self,closure_notes_content):
        from deepeval.test_case import LLMTestCase,LLMTestCaseParams
        from deepeval.metrics import GEval
        from agents.Quiz_Generator_Agent import generate_questions

        print("\n[TestQuizQuality] Generating quiz questions...")

        questions = generate_questions(
            topic="Python Closures",
            explanation=closure_notes_content,
            n=2,
        )

        questions_text = "\n".join([
            f"Q{i+1}: {q['question']}\nExpected: {q['expected_answer']}"
            for i, q in enumerate(questions)
        ])

        test_case = LLMTestCase(
            input="Generate quiz questions about Python closures that tests user's understanding about the topic",
            actual_output=questions_text,
        )

        metric = GEval(
            name="QuestionQuality",
            criteria=(
                "Evaluate whether these quiz questions test genuine conceptual "
                "understanding of Python closures rather than surface-level recall. "
                "Good questions require the student to: apply concepts to new situations, "
                "explain WHY something works, identify edge cases, or compare concepts. "
                "Poor questions only ask to define terms or recite examples from the notes."
            ),
            evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT],
            model="gpt-4o-mini",
            threshold=self.QUESTION_QUALITY_THRESHOLD,
        )

        metric.measure(test_case)

        print(f"\n[QuestionQuality] Score: {metric.score:.3f} "
              f"(threshold: {self.QUESTION_QUALITY_THRESHOLD})")
        if hasattr(metric, "reason") and metric.reason:
            print(f"[QuestionQuality] Reason: {metric.reason}")

        assert metric.score >= self.QUESTION_QUALITY_THRESHOLD, (
            f"Question quality score {metric.score:.3f} below threshold.\n"
            "Questions may be too surface-level.\n"
            f"Questions generated:\n{questions_text}"
        )
