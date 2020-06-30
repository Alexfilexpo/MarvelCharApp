import copy
import random
import jmespath
import hashlib
import json
from datetime import datetime
from requests import get
from django.shortcuts import render
from django.views.generic import View
from django.utils.safestring import mark_safe
from .forms import CharacterForm

timestamp = datetime.now().strftime('%Y-%m-%d%H:%M:%S')
apikey = 'f4140cedc75bd4b121b6595234284bb0'
prikey = '911b9d52548b3a7723510d9dac6b1d9c7bceeaf6'
hash = hashlib.md5(f'{timestamp}{prikey}{apikey}'.encode('utf-8')).hexdigest()
req_params = {'ts': timestamp, 'apikey': apikey, 'hash': hash}

characters_endpoint = 'https://gateway.marvel.com:443/v1/public/characters'
stories_endpoint = 'https://gateway.marvel.com:443/v1/public/stories'
comics_endpoint = 'https://gateway.marvel.com:443/v1/public/comics'


class SearchForm(View):
    def get(self, request):
        form = CharacterForm()
        return render(request, 'marvelapp/search_form.html', context={'form': form})

    def resp_validator(self, response):
        """
        Validate if response have any results

        Parameters:
            response (json) - response body
        Returns:
            (bool) - True if there is any results, False - if not
        """
        isresults = jmespath.search('data.results', response)
        return bool(isresults)

    def edit_req_param(self, name, value):
        """
        Edit request parameters for specified endpoint

        Parameters:
            name (str) - name of parameter
            value (str) - value of parameter
        Returns:
            spec_req_params (dict) - updated parameters for specified endpoint
        """
        spec_req_params = copy.deepcopy(req_params)
        spec_req_params[name] = value
        return spec_req_params

    def find_hero_info(self, hero_name):
        """
        Sending request to MarverlAPI's characters endpoint for hero data

        Parameters:
            hero_name (str) - name of superhero from Search Form
        Returns:
            dict: hero_id (int) - id of superhero in database, hero_img (str) - url of superhero image
        """
        spec_req_params = self.edit_req_param('name', hero_name)
        hero_response = get(characters_endpoint, params=spec_req_params)
        resp_body = json.loads(hero_response.text)
        is_data = self.resp_validator(resp_body)
        if not is_data:
            return 'No results'
        hero_id = jmespath.search('data.results[0].id', resp_body)
        hero_img_data = jmespath.search('data.results[0].thumbnail.[path, extension]', resp_body)
        hero_img = '.'.join(hero_img_data)
        return {
            'hero_id': hero_id,
            'hero_img': hero_img
        }

    def get_hero_stories(self, hero_id):
        """
        Sending request to MarverlAPI's stories endpoint for all stories connected with superhero and get attribution text

        Parameters:
            hero_id (int) - id of superhero
        Returns:
            list - list of all stories data
        """
        spec_req_params = self.edit_req_param('characters', hero_id)
        stories_response = get(stories_endpoint, params=spec_req_params)
        stories_list = json.loads(stories_response.text)
        attr_text = jmespath.search("attributionHTML", stories_list)
        return {
            'stories_list': stories_list,
            'attr_text': attr_text
        }

    def random_story_data(self, stories_list):
        """
        Getting random story data from stories list

        Parameters:
            stories_list (list) - list of stories
        Returns:
            dict: story_id - id of story, story_data - full data of specified story,
                    store_desc - description of story, story_title - title of story
        """
        stories_ids = jmespath.search('data.results[*].id', stories_list)
        random_index = random.randint(0, len(stories_ids)-1)
        story_id = stories_ids[random_index]
        story_data = jmespath.search(f"data.results[?id==`{story_id}`]", stories_list)
        story_description = jmespath.search("[].description", story_data)
        story_title = jmespath.search("[].title", story_data)
        return {
            'story_id': story_id,
            'story_data': story_data,
            'story_desc': story_description,
            'story_title': story_title
        }

    def comic_data(self, story_id):
        """
        Sending request to MarverlAPI's comics endpoint for comic specified by story "id" in it

        Parameters:
            story_id (int) - "id" of story
        Returns:
            dict: comic_name - title of comic, comic_img_url - url of comic cover image
        """
        spec_req_params = self.edit_req_param('stories', story_id)
        comic_response = get(comics_endpoint, params=spec_req_params)
        comic_data = json.loads(comic_response.text)
        comic_name = jmespath.search('data.results[0].title', comic_data)
        comic_img_data = jmespath.search('data.results[0].images[0].[path, extension]', comic_data)
        comic_img_url = '.'.join(comic_img_data)
        return {
            'comic_name': comic_name,
            'comic_img_url': comic_img_url
        }

    def get_story_heroes(self, story_data):
        """
        Getting all superheroes in specified story and sending request to MarverlAPI's characters endpoint
        for info for each superhero

        Parameters:
            story_data (dict) - complete data of specified story
        Returns:
            dict: {hero_name}: {hero_img_url} - for each superhero name - it's own image
        """
        characters = jmespath.search("[0].characters.items[*].name", story_data)
        heroes_data = {}
        for hero in characters:
            hero_data = self.find_hero_info(hero)
            heroes_data[hero] = hero_data['hero_img']
        return heroes_data

    def post(self, request):
        name = request.POST['name']
        hero_data = self.find_hero_info(name)
        if hero_data == 'No results':
            form = CharacterForm()
            return render(request, 'marvelapp/error.html', context={'form': form})
        stories = self.get_hero_stories(hero_data['hero_id'])
        story_data = self.random_story_data(stories['stories_list'])
        com_data = self.comic_data(story_data['story_id'])
        heroes_data = self.get_story_heroes(story_data['story_data'])
        context = {
            'story_desc': story_data['story_desc'][0],
            'story_title': story_data['story_title'][0],
            'attribution_text': mark_safe(stories['attr_text']),
            'com_data': com_data,
            'heroes_data': heroes_data
        }
        return render(request, 'marvelapp/result.html', context=context)
