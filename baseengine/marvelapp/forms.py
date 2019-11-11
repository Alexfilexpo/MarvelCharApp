from django import forms


class CharacterForm(forms.Form):
    name = forms.CharField(max_length=50)

    name.widget.attrs.update({'class': 'form-control', 'style': 'border: 1px solid grey;'})