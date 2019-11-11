from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Tag, Recipe

from recipe.serializers import TagSerializer


TAGS_URL = reverse('recipe:tag-list')


class PublicTagsApiTests(TestCase):
    """ test the publicly available tags API """

    def setUp(self):
        self.client = APIClient()

    def test_login_required(self):
        """ test that login is required for retirieving tags """
        res = self.client.get(TAGS_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateTagsApiTests(TestCase):
    """ test the authorized user tags API """

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email='test@gmail.com',
            password='test1234'
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_retrieve_tags(self):
        """ test retrieving tags """
        Tag.objects.create(user=self.user, name='vegan')
        Tag.objects.create(user=self.user, name='dessert')

        res = self.client.get(TAGS_URL)

        tags = Tag.objects.all().order_by('-name')
        serializer = TagSerializer(tags, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_tags_limited_to_user(self):
        """ test that tags returned are for the authenticated user """
        user2 = get_user_model().objects.create_user(
            'other@gmail.com',
            'tnantanta'
        )

        Tag.objects.create(user=user2, name='fruity')
        tag = Tag.objects.create(user=self.user, name='food')

        res = self.client.get(TAGS_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['name'], tag.name)

    def test_create_tag_successful(self):
        """ test creating a new tag """
        payload = {'name': 'test tag'}
        self.client.post(TAGS_URL, payload)

        exists = Tag.objects.filter(user=self.user,
                                    name=payload['name']).exists()
        self.assertTrue(exists)

    def test_create_tag_invalid(self):
        """ test creating a new tag with invalid payload """
        payload = {}
        res = self.client.post(TAGS_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_retrieve_tags_assigned_to_recipes(self):
        """ test filtering tags by those assigned to recipes """
        tag1 = Tag.objects.create(user=self.user, name='breakfast')
        tag2 = Tag.objects.create(user=self.user, name='lunch')

        recipe = Recipe.objects.create(
            title='coriander eggs on toast',
            time_minutes=10,
            price=50,
            user=self.user
        )

        recipe.tags.add(tag1)

        res = self.client.get(TAGS_URL, {'assigned_only': 1})

        serializer1 = TagSerializer(tag1)
        serializer2 = TagSerializer(tag2)

        self.assertIn(serializer1.data, res.data)
        self.assertNotIn(serializer2.data, res.data)

    def test_retrieve_tags_assigned_unique(self):
        """ test filtering tags by assigned returns unique items """
        tag = Tag.objects.create(user=self.user, name='breakfast')
        Tag.objects.create(user=self.user, name='lunch')

        recipe1 = Recipe.objects.create(
            user=self.user,
            title='pancake',
            price=5.00,
            time_minutes=4
        )

        recipe1.tags.add(tag)
        recipe2 = Recipe.objects.create(
            title='porridge',
            time_minutes=3,
            price=3.00,
            user=self.user
        )

        recipe2.tags.add(tag)

        res = self.client.get(TAGS_URL, {'assigned_only': 1})

        self.assertEqual(len(res.data), 1)
