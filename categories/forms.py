from django import forms
from .models import categories

class categoryform(forms.ModelForm):
  image = forms.ImageField(required=False)

  
  class Meta:
    model=categories
    fields=['name','description','is_listed','image']