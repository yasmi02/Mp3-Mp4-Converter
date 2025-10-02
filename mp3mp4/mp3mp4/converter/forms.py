from django import forms

class DownloadForm(forms.Form):
    url = forms.CharField(
        widget=forms.TextInput(attrs={
            'style': 'min-height: 40px; padding: 15px 14px; font-size: 18px;',
            'placeholder': 'Paste your video URL here...'
        })
    )
    format = forms.ChoiceField(choices=[('mp3', 'MP3'), ('mp4', 'MP4')])