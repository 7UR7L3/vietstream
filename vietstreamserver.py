import wave

from subprocess import Popen, PIPE

import time

from io import BytesIO
import flask

import os

import json

import re


# thanks timber
# thanks https://opus-codec.org/downloads/



wordsToSegment = {}; # temporary map from a single word to [(resource, start, end)] ; can't really do this if i want to be able to stream any phrase...

for file in os.listdir( "aligned vivos test" ):
	if file.endswith( ".json" ):
		with open( os.path.join( ".", "aligned vivos test", file ), 'r', encoding="utf8") as f:
			j = json.load( f );
			for item in j["tiers"][0]["items"]:
				if item["text"] not in wordsToSegment: wordsToSegment[item["text"]] = [];
				wordsToSegment[item["text"]].append( ( file, float(item["xmin"]), float(item["xmax"]) ) );












def makeOpusResponse( sourceWav, start=None, end=None ): # returns slice of sourceWav as opus; start and end are in seconds
	# TODO cache response.. think there's a decorator for this

	### read .wav file into wave object
	sourceWaveObj = wave.open( sourceWav, "rb" ); # thanks https://stackoverflow.com/a/38523274
	
	### extract target frames from wave object
	if start is not None: sourceWaveObj.setpos( int( start * sourceWaveObj.getframerate() ) );

	if end is not None:
		sourceSnippetFrames = sourceWaveObj.readframes( int( (end-start) * sourceWaveObj.getframerate() ) );
	else: # read to the end of the file
		sourceSnippetFrames = sourceWaveObj.readframes( sourceWaveObj.getnframes() - sourceWaveObj.tell() );

	### write frames to in-memory .wav file
	sourceSnippet = BytesIO();
	sourceSnippetWv = wave.open( sourceSnippet, "wb" );
	sourceSnippetWv.setnchannels( sourceWaveObj.getnchannels() );
	sourceSnippetWv.setframerate( sourceWaveObj.getframerate() );
	sourceSnippetWv.setsampwidth( sourceWaveObj.getsampwidth() );
	sourceSnippetWv.writeframes( sourceSnippetFrames );
	sourceSnippet = sourceSnippet.getvalue();
	
	sourceWaveObj.close();

	### convert snippet .wav file to .opus file
	opusResp = Popen( "opusenc - -".split(), stdout=PIPE, stdin=PIPE, stderr=PIPE ) \
				.communicate( input=sourceSnippet )[0] # thanks https://stackoverflow.com/a/8475367

	### respond with .opus file
	memFile = BytesIO(); # thanks https://stackoverflow.com/a/17365399
	memFile.write( opusResp );
	response = flask.make_response( memFile.getvalue() );
	memFile.close();

	response.headers["Content-Type"] = "audio/ogg";
	response.headers["Content-Disposition"] = "attachment; filename=snippet.opus";
	# response.headers["Cache-Control"] = "public, no-transform, max-age=31536000";
	response.headers["Cache-Control"] = "no-cache, max-age=0"; # TODO correct this to cache aggressively after testing

	return response;





app = flask.Flask(__name__);

@app.route( "/vietstream.opus" )
def vietstream():
	params = flask.request.args;
	print( f"\nrequesting audio {dict(params)}" );

	segment = wordsToSegment[params["q"]];
	n = int(params["n"]) % len(segment); # not sure if i like giving them the mod of what they request but it's fine for a good while; TODO ponder 404ing or something if n is out of bounds
	segn = segment[n];
	start, end = segn[1], segn[2] # in seconds

	response = makeOpusResponse( os.path.join( ".", "aligned vivos test", segn[0].replace(".json", ".wav") ), start, end );

	return response;

@app.route( "/" )
def root():
    return re.sub( "\n    ", "\n", """<pre>
    Hello! Welcome to the Viet Audio Stream server.


    This server allows for querying for vietnamese audio
    from corresponding search text.

    The audio has been pre-aligned to text with the Montreal
    Forced Aligner at the word and phone level.


    Current audio/text is sourced from the following resources:
        [VIVTST] -- VIVOS Corpus test set
    (-) [HP1CH1] -- chapter 1 of Lý Lan's Harry Potter và Hòn Đá Phù Thủy audiobook



    Viet Audio Stream API Usage:

    /vietstream.opus             -- request audio; returns .opus file
    (p) ?q=[SEARCH QUERY]        -- any regular expression; queries for matching utterances
                                    n.b. `[a]` may be used as shorthand for `[aáàảãạ]`
        &n=[SEARCH RESULT IDX]   -- any non negative integer; index into the result set to return
    (-) &pad=[PAD AMOUNT]        -- amount of padding around the result (default minimal padding)
                                    e.g. `2w` for two words before and after,
                                         `3p` for three phones before and after,
                                         `sent` for the enclosing sentence,
                                         `b` for the bordering word/phone time boundary
    (-) &level=[ALIGNMENT LEVEL] -- either `word` or `phone` (default `word`);
                                    if `phone`, result set consists of minimal matching audio
    (-) &bitrate=[BITRATE]       -- any target bitrate (6-256 per channel, in kbit/s) 

    (-)
    /vietstream.json             -- request information about a search result,
                                    follows the same format as /vietstream.opus
                                    with the additional parameter
        &info=[INFO TO RETURN]   -- which information to return (default `all`)
                                    e.g. `tn` for the corresponding text and total results count,
                                         `a` for just the alignment

        returns information in the following json format:
        {
            text: [RESULT TEXT],        -- the corresponding text to the audio
            numResults: [RESULT COUNT], -- the total number of matches in the result set
            alignment: [TEXTGRID]       -- textgrid json containing word and phone alignments
        }

    (-)
    /[RESOURCE IDENTIFIER] -- request information about a given resource
                              includes information such as dialect, total length in text and audio,
                              source/mirrors, alignment download links


    Note (-) marks yet to be implemented items and (p) marks in progress items.
    </pre>
    """ );

if __name__ == "__main__":
	app.run( host='0.0.0.0', debug=True, threaded=True,port=5000 )



"""
TODOs

- maybe support fully speech to text ones from news sources like https://www.voatiengviet.com/z/1952 cause like news is super clear...
- so probably a allowSTT=true param or further restrictTo to restrict to those news ones..
  prolly with a resource identifier that encapsulates all news or all stt

- be able to request a custom bitrate; bitrate 6 doesn't sound completely trash and is TINY
- make api like this .../vietstream?q=tôi - any regular expression
	                            &dialect=[n|s]
	                            &restrictTo=muav,seca,torf - or whatever unique identifiers a resource is assigned
	                            &n=123 - to get the specific result
- and an endpoint /vietstream?numResults to get the number of results possibly
  OR just leaving off the n parameter would give the number of results and maybe other json..
  but probably a /vietstreamInfo would work to get numResults and any other information...
 
- only other important thing is to get padding around the query text...
  probably requesting n words before and after, or the whole sentence containing the word
  maybe like pad=1w or 2w or 5s or sent

- actually doing that ^ would make the /vietstream.opus vs /vietstream.json pretty hot where the json returns the text of the excerpt with the textgrid data

- also make /vietstream give some nice help text for how to use the api

- viaustream .. ViAuStream ? eh? i don't like it lol. i like vietstream as a url short for Viet Audio Stream i guess

- should probably have a general cut api where you request a specific resource and the start and end time; cause why not
"""