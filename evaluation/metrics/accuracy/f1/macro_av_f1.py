"""
This is the implementation of the F-score metric.
It proceeds from a user-wise computation, and average the values over the users.
"""

__version__ = '0.1'
__author__ = 'Vito Walter Anelli, Claudio Pomo'
__email__ = 'vitowalter.anelli@poliba.it, claudio.pomo@poliba.it'

import numpy as np
from elliot.evaluation.metrics.base_metric import BaseMetric


class MavF1(BaseMetric):
    r"""
    F-Measure

    This class represents the implementation of the F-score recommendation metric.
    Passing 'F1' to the metrics list will enable the computation of the metric.

    For further details, please refer to the `paper <https://link.springer.com/chapter/10.1007/978-1-4899-7637-6_8>`_

    .. math::
        \mathrm {F1@K} = \frac{1+\beta^{2}}{\frac{1}{\text { precision@k }}+\frac{\beta^{2}}{\text { recall@k }}}

    To compute the metric, add it to the config file adopting the following pattern:

    .. code:: yaml

        simple_metrics: [F1]
    """

    def __init__(self, recommendations, config, params, eval_objects):
        """
        Constructor
        :param recommendations: list of recommendations in the form {user: [(item1,value1),...]}
        :param config: SimpleNameSpace that represents the configuration of the experiment
        :param params: Parameters of the model
        :param eval_objects: list of objects that may be useful for the computation of the different metrics
        """
        super().__init__(recommendations, config, params, eval_objects)
        self._cutoff = self._evaluation_objects.cutoff
        self._relevance = self._evaluation_objects.relevance.binary_relevance
        self.precision = []
        self.recall = []
        self.f1_score = 0

    @staticmethod
    def name():
        """
        Metric Name Getter
        :return: returns the public name of the metric
        """
        return "MavF1"

    def precision_recall(self, user_recommendations, cutoff, user_relevant_items):
        """
        Per User F-score
        :param user_recommendations: list of user recommendation in the form [(item1,value1),...]
        :param cutoff: numerical threshold to limit the recommendation list
        :param user_relevant_items: list of user relevant items in the form [item1,...]
        :return: the value of the Precision metric for the specific user
        """
        if len(user_relevant_items):
            self.precision.append(sum([1 for i in user_recommendations[:cutoff] if i[0] in user_relevant_items]) / cutoff)
            self.recall.append(sum([1 for i in user_recommendations[:cutoff] if i[0] in user_relevant_items]) / len(user_relevant_items))
        else:
            self.precision.append(0)
            #self.recall.append(0)

    def score(self):
        p_sum = 0
        r_sum = 0
        for p in self.precision:
            p_sum += p
        for r in self.recall:
            r_sum += r
        averaged_p = p_sum/len(self.precision)
        averaged_r = r_sum/len(self.recall)
        self.f1_score = 2 * averaged_p * averaged_r / (averaged_p + averaged_r) if (averaged_p + averaged_r) != 0 else 0

    def __user_f1(self):
        return self.f1_score

    # def eval(self):
    #     """
    #     Evaluation function
    #     :return: the overall averaged value of F-score
    #     """
    #     return np.average(
    #         [F1.__user_f1(u_r, self._cutoff, self._relevant_items[u], self._squared_beta)
    #          for u, u_r in self._recommendations.items() if len(self._relevant_items[u])]
    #     )

    def eval_user_metric(self):
        """
        Evaluation function
        :return: the overall averaged value of F-score
        """
        for u, u_r in self._recommendations.items():
                self.precision_recall(u_r, self._cutoff, self._relevance.get_user_rel(u))
        self.score()
        return {u: MavF1.__user_f1(self)
                for u, u_r in self._recommendations.items() if len(self._relevance.get_user_rel(u))}
