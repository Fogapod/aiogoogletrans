"""
A Translation module.

You can translate text using this module.
"""
import aiohttp
import random
import asyncio

from aiogoogletrans import urls, utils
from aiogoogletrans.constants import DEFAULT_USER_AGENT, LANGCODES, LANGUAGES, SPECIAL_CASES
from aiogoogletrans.models import Translated

from gtts_token import gtts_token


EXCLUDES = ('en', 'ca', 'fr')


class Translator:
    """Google Translate ajax API implementation class

    You have to create an instance of Translator to use this API

    :param session: session to use, new one is created if not passed
    :type session: :class:`aiohttp.ClientSession`

    :param service_urls: google translate url list. URLs will be used randomly.
                         For example ``['translate.google.com', 'translate.google.co.kr']``
    :type service_urls: a sequence of strings

    :param user_agent: the User-Agent header to send when making requests.
    :type user_agent: :class:`str`

    :param proxies: list of proxy urls, random proxy is used for each request
                    Notice: client won't send direct requests if at least 1 proxy is passed,
                    include None in list to let client send direct requests
    :type proxies: list: :class:`list`

    :type loop: asyncio event loop. If not passed, asyncio.get_event_loop() will be called
    """

    def __init__(
            self, session=None, service_urls=None, user_agent=DEFAULT_USER_AGENT,
            proxies=None, loop=asyncio.get_event_loop()
        ):

        self.headers = {
            'User-Agent': user_agent,
        }
        self.session = session
        self.proxies = proxies or [None]

        self.service_urls = service_urls or ['translate.google.com']

        self.loop = loop

        self.token = gtts_token.Token()

    async def _make_session(self):
        self.session = aiohttp.ClientSession(headers=self.headers)

    def _pick_service_url(self):
        if len(self.service_urls) == 1:
            return self.service_urls[0]
        return random.choice(self.service_urls)

    def _pick_proxy(self):
        if len(self.proxies) == 1:
            return self.proxies[0]
        return random.choice(self.proxies)

    async def _translate(self, text, dest, src, proxy):
        if self.session is None:
            await self._make_session()

        token = await self.loop.run_in_executor(
            None, self.token.calculate_token, text)

        params = utils.build_params(query=text, src=src, dest=dest,
                                    token=token)
        url = urls.TRANSLATE.format(host=self._pick_service_url())

        async with self.session.get(f'{url}?{params}', proxy=proxy) as resp:
            text = await resp.text()

        return utils.format_json(text)

    async def translate(self, text, **kwargs):
        """Translate text from source language to destination language

        :param text: The source text(s) to be translated. Batch translation is supported via sequence input.
        :type text: UTF-8 :class:`str`; string sequence (list, tuple, iterator, generator)

        :param dest: The language to translate the source text into.
                     The value should be one of the language codes listed in :const:`googletrans.LANGUAGES`
                     or one of the language names listed in :const:`googletrans.LANGCODES`.
        :param dest: :class:`str`

        :param src: The language of the source text.
                    The value should be one of the language codes listed in :const:`googletrans.LANGUAGES`
                    or one of the language names listed in :const:`googletrans.LANGCODES`.
                    If a language is not specified,
                    the system will attempt to identify the source language automatically.
        :param src: :class:`str`

        :param proxy: A proxy to use, can be None. If not provided, random session proxy is used.
        :param proxy: class:`str`

        :rtype: Translated
        :rtype: :class:`list` (when a list is passed)

        Basic usage:
            >>> from aiogoogletrans import Translator
            >>> translator = Translator()
            >>> await translator.translate('안녕하세요.')
            <Translated src=ko dest=en text=Good evening. pronunciation=Good evening.>
            >>> await translator.translate('안녕하세요.', dest='ja')
            <Translated src=ko dest=ja text=こんにちは。 pronunciation=Kon'nichiwa.>
            >>> await translator.translate('veritas lux mea', src='la')
            <Translated src=la dest=en text=The truth is my light pronunciation=The truth is my light>

        Advanced usage:
            >>> translations = translator.translate(['The quick brown fox', 'jumps over', 'the lazy dog'], dest='ko')
            >>> for translation in translations:
            ...    print(translation.origin, ' -> ', translation.text)
            The quick brown fox  ->  빠른 갈색 여우
            jumps over  ->  이상 점프
            the lazy dog  ->  게으른 개
        """

        dest = kwargs.pop('dest', None)
        if dest is None:
            dest = 'en'
        else:
            dest = dest.partition('_')[0].lower()

        src = kwargs.pop('src', None)
        if src is None:
            src = 'auto'
        else:
            src = src.partition('_')[0].lower()


        proxy = kwargs.pop('proxy', self._pick_proxy())

        if kwargs:
            raise TypeError(
                f"translate() got an unexpected keyword argument '{list(kwargs.keys())[0]}'")

        if src != 'auto' and src not in LANGUAGES:
            if src in SPECIAL_CASES:
                src = SPECIAL_CASES[src]
            elif src in LANGCODES:
                src = LANGCODES[src]
            else:
                raise ValueError('invalid source language')

        if dest not in LANGUAGES:
            if dest in SPECIAL_CASES:
                dest = SPECIAL_CASES[dest]
            elif dest in LANGCODES:
                dest = LANGCODES[dest]
            else:
                raise ValueError('invalid destination language')

        if isinstance(text, list):
            result = []
            for item in text:
                # FIXME: in case proxy was randomly picked before, now it will
                # be enforced for all requests
                translated = await self.translate(
                    item, dest=dest, src=src, proxy=proxy)
                result.append(translated)
            return result

        origin = text
        data = await self._translate(text, dest, src, proxy=proxy)

        # this code will be updated when the format is changed.
        translated = ''.join([d[0] if d[0] else '' for d in data[0]])

        pron = origin
        try:
            pron = data[0][1][-1]
        except Exception:  # pragma: nocover
            pass
        if dest in EXCLUDES and pron == origin:
            pron = translated


        src_detected, confidence = '', 0.0
        try:
            src_detected, confidence = ''.join(data[8][0]), data[8][-2][0]
        except:
            pass

        # put final values into a new Translated object
        result = Translated(
            src=src_detected, confidence=confidence, dest=dest, origin=origin,
            text=translated, pronunciation=pron,
        )

        return result

    async def close(self):
        """Perform cleanup"""
        if self.session is not None:
            await self.session.close()
