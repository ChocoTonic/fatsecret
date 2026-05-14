"""Resource-namespaced API surface for v2.0.

Each resource maps 1:1 to an OAS tag from `docs/api-spec/openapi.yaml`.
Phase 1 (this commit): pure-delegation wrappers over the flat `_vN`
methods that already live on `Fatsecret`. No behavior change.

Future phases swap delegation for fully generated implementations.
"""

from .classification import ClassificationResource
from .diary import DiaryResource
from .exercises import ExercisesResource
from .feedback import FeedbackResource
from .foods import FoodsResource
from .meals import MealsResource
from .native import NativeResource
from .profile import ProfileResource
from .profile_foods import ProfileFoodsResource
from .recipes import RecipesResource
from .weight import WeightResource

__all__ = [
    "ClassificationResource",
    "DiaryResource",
    "ExercisesResource",
    "FeedbackResource",
    "FoodsResource",
    "MealsResource",
    "NativeResource",
    "ProfileFoodsResource",
    "ProfileResource",
    "RecipesResource",
    "WeightResource",
]
