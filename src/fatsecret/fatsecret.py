"""
fatsecret
---------

Simple python wrapper of the Fatsecret API

"""

from .core import FatsecretCore
from .exercises import ExercisesMixin
from .foods import FoodsMixin
from .meals import MealsMixin
from .profile import ProfileMixin
from .recipes import RecipesMixin
from .weight import WeightMixin


# FIXME add method to set default units and make it an optional argument to the constructor
class Fatsecret(
    ExercisesMixin,
    FatsecretCore,
    FoodsMixin,
    MealsMixin,
    ProfileMixin,
    RecipesMixin,
    WeightMixin,
):
    """Unified Fatsecret API client with all functionality via mixins"""

    pass
