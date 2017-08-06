#!/usr/bin/env python

import logging
logger = logging.getLogger(__name__)

class BaseCodec(object):
    """
    Base audio/video codec class.
    """

    encoder_options = {}
    codec_name = None
    ffmpeg_codec_name = None

    def parse_options(self, opt):
        if 'codec' not in opt or opt['codec'] != self.codec_name:
            raise ValueError('invalid codec name')
        return None

    def _codec_specific_parse_options(self, safe):
        return safe

    def _codec_specific_produce_ffmpeg_list(self, safe):
        return []

    def safe_options(self, opts):
        safe = {}

        # Only copy options that are expected and of correct type
        # (and do typecasting on them)
        for k, v in opts.items():
            if k in self.encoder_options:
                typ = self.encoder_options[k]
                try:
                    safe[k] = typ(v)
                except:
                    pass

        return safe


class AudioCodec(BaseCodec):
    """
    Base audio codec class handles general audio options. Possible
    parameters are:
      * codec (string) - audio codec name
      * channels (integer) - number of audio channels
      * bitrate (integer) - stream bitrate
      * samplerate (integer) - sample rate (frequency)

    Supported audio codecs are: null (no audio), copy (copy from
    original), vorbis, aac, mp3, mp2
    """

    encoder_options = {
        'codec': str,
        'channels': int,
        'bitrate': int,
        'samplerate': int,
        'filters': str
    }

    def _extend_af(self, optlist, value):

        if not value:
            return optlist

        if optlist.count('-af'):
            current_af = optlist[optlist.index('-af') + 1]
            new_af = "{0},{1}".format(current_af, value)  # append filters to current
            optlist[optlist.index('-af') + 1] = new_af
        else:
            optlist.extend(['-af', value])
        return optlist

    def parse_options(self, opt):
        super(AudioCodec, self).parse_options(opt)

        safe = self.safe_options(opt)

        if 'channels' in safe:
            c = safe['channels']
            if c < 1 or c > 12:
                del safe['channels']

        if 'bitrate' in safe:
            br = safe['bitrate']
            if br < 8 or br > 512:
                del safe['bitrate']

        if 'samplerate' in safe:
            f = safe['samplerate']
            if f < 1000 or f > 50000:
                del safe['samplerate']

        safe = self._codec_specific_parse_options(safe)

        optlist = ['-c:a', self.ffmpeg_codec_name]
        if 'channels' in safe:
            optlist.extend(['-ac', str(safe['channels'])])
        if 'bitrate' in safe:
            optlist.extend(['-ab', str(safe['bitrate']) + 'k'])
        if 'samplerate' in safe:
            optlist.extend(['-ar', str(safe['samplerate'])])
        if 'volume' in safe:
            optlist.extend(['-af', 'volume={0:.1f}dB'.format(safe['volume'])])
        if 'filters' in safe:
            optlist = self._extend_af(optlist, safe['filters'])

        optlist.extend(self._codec_specific_produce_ffmpeg_list(safe))
        return optlist


class SubtitleCodec(BaseCodec):
    """
    Base subtitle codec class handles general subtitle options. Possible
    parameters are:
      * codec (string) - subtitle codec name (mov_text, subrib, ssa only supported currently)
      * language (string) - language of subtitle stream (3 char code)
      * forced (int) - force subtitles (1 true, 0 false)
      * default (int) - default subtitles (1 true, 0 false)

    Supported subtitle codecs are: null (no subtitle), mov_text
    """

    encoder_options = {
        'codec': str,
        'language': str,
        'forced': int,
        'default': int
    }

    def parse_options(self, opt):
        super(SubtitleCodec, self).parse_options(opt)
        safe = self.safe_options(opt)

        if 'forced' in safe:
            f = safe['forced']
            if f < 0 or f > 1:
                del safe['forced']

        if 'default' in safe:
            d = safe['default']
            if d < 0 or d > 1:
                del safe['default']

        if 'language' in safe:
            l = safe['language']
            if len(l) > 3:
                del safe['language']

        safe = self._codec_specific_parse_options(safe)

        optlist = ['-c:s', self.ffmpeg_codec_name]

        optlist.extend(self._codec_specific_produce_ffmpeg_list(safe))
        return optlist

class DecoderCodec(BaseCodec):
    """
    """
    encoder_options = {
        'codec': str,
    }
    
    def parse_options(self, opt):
        super(DecoderCodec, self).parse_options(opt)
        safe = self.safe_options(opt)
        safe = self._codec_specific_parse_options(safe)

        optlist = ['-decoder', self.ffmpeg_codec_name]
        
        optlist.extend(self._codec_specific_produce_ffmpeg_list(safe))
        return optlist

class VideoCodec(BaseCodec):
    """
    Base video codec class handles general video options. Possible
    parameters are:
      * codec (string) - video codec name
      * bitrate (float) - stream bitrate
      * fps (float) - frames per second
      * max_width (integer) - video width
      * max_height (integer) - video height
      * filters (string) - filters (flip, rotate, etc)
      * sizing_policy (string) - aspect preserval mode; one of:
            ...
      * src_width (int) - source width
      * src_height (int) - source height
      * src_rotate (90) -

    Aspect preserval mode is only used if both source
    and both destination sizes are specified. If source
    dimensions are not specified, aspect settings are ignored.

    If source dimensions are specified, and only one
    of the destination dimensions is specified, the other one
    is calculated to preserve the aspect ratio.

    Supported video codecs are: null (no video), copy (copy directly
    from the source), Theora, H.264/AVC, DivX, VP8, H.263, Flv,
    MPEG-1, MPEG-2.
    """

    encoder_options = {
        'codec': str,
        'bitrate': float,
        'fps': float,
        'pix_fmt': str,
        'max_width': int,
        'max_height': int,
        'sizing_policy': str,
        'src_width': int,
        'src_height': int,
        'src_rotate': int,
        'crop': str,
        'filters': str,
        'autorotate': bool,
        'bufsize': int,
    }

    def _autorotate(self, src_rotate):
        filters = {
            90: "transpose=1",
            180: "transpose=2,transpose=2",
            270: "transpose=2"
        }
        return filters.get(src_rotate)

    def _extend_vf(self, optlist, value):

        if not value:
            return optlist

        if optlist.count('-vf'):
            current_vf = optlist[optlist.index('-vf') + 1]
            new_vf = "{0},{1}".format(current_vf, value)  # append filters to current
            optlist[optlist.index('-vf') + 1] = new_vf
        else:
            optlist.extend(['-vf', value])
        return optlist

    def _div_by_2(self, d):
        return float(d) + 1 if float(d) % 2 else float(d)

    def _aspect_corrections(self, sw, sh, max_width, max_height, sizing_policy):
        if not max_width or not max_height or not sw or not sh:
            return sw, sh, None

        if sizing_policy not in ['Fit', 'Fill', 'Stretch', 'Keep', 'ShrinkToFit', 'ShrinkToFill']:
            print ("invalid option "+sizing_policy)
            return sw, sh, None

        """
        Fit: FFMPEG scales the output video so it matches the value
        that you specified in either Max Width or Max Height without exceeding the other value."
        """
        if sizing_policy == 'Fit':
            if float(sh / sw) == float(max_height):
                return max_width, max_height, None
            elif float(sh / sw) < float(max_height):  # scaling height
                factor = float(float(max_height) / float(sh))
                return int(sw * factor), max_height, None
            else:
                factor = float(float(max_width) / float(sw))
                return max_width, int(sh * factor), None

        """
        Fill: FFMPEG scales the output video so it matches the value that you specified
        in either Max Width or Max Height and matches or exceeds the other value. Elastic Transcoder
        centers the output video and then crops it in the dimension (if any) that exceeds the maximum value.
        """
        if sizing_policy == 'Fill':
            if float(sh / sw) == float(max_height):
                return max_width, max_height, None
            elif float(sh / sw) < float(max_height):  # scaling width
                factor = float(float(max_width) / float(sw))
                h0 = int(sh * factor)
                dh = (h0 - max_height) / 2
                return max_width, h0, 'crop={0}:{1}:{2}:0'.format(max_width, max_height, dh)
            else:
                factor = float(float(max_height) / float(sh))
                w0 = int(sw * factor)
                dw = (w0 - max_width) / 2
                return w0, max_height, 'crop={0}:{1}:{2}:0'.format(max_width, max_height, dw)

        """
        Stretch: FFMPEG stretches the output video to match the values that you specified for Max
        Width and Max Height. If the relative proportions of the input video and the output video are different,
        the output video will be distorted.
        """
        if sizing_policy == 'Stretch':
            return max_width, max_height, None

        """
        Keep: FFMPEG does not scale the output video. If either dimension of the input video exceeds
        the values that you specified for Max Width and Max Height, FFMPEG crops the output video.
        """
        if sizing_policy == 'Keep':
            return sw, sh, None

        """
        ShrinkToFit: FFMPEG scales the output video down so that its dimensions match the values that
        you specified for at least one of Max Width and Max Height without exceeding either value. If you specify
        this option, Elastic Transcoder does not scale the video up.
        """
        if sizing_policy == 'ShrinkToFit':
            if sh > max_height or sw > max_width:
                if float(sh / sw) == float(max_height):
                    return max_width, max_height, None
                elif float(sh / sw) < float(max_height):  # target is taller
                    factor = float(float(max_height) / float(sh))
                    return int(sw * factor), max_height, None
                else:
                    factor = float(float(max_width) / float(sw))
                    return max_width, int(sh * factor), None
            else:
                return sw, sh, None

        """
        ShrinkToFill: FFMPEG scales the output video down so that its dimensions match the values that
        you specified for at least one of Max Width and Max Height without dropping below either value. If you specify
        this option, FFMPEG does not scale the video up.
        """
        if sizing_policy == 'ShrinkToFill':
            if sh < max_height or sw < max_width:
                if float(sh / sw) == float(max_height):
                    return max_width, max_height, None
                elif float(sh / sw) < float(max_height):  # scaling width
                    factor = float(float(max_width) / float(sw))
                    h0 = int(sh * factor)
                    dh = (h0 - max_height) / 2
                    return max_width, h0, 'crop=%d:%d:%d:0' % (max_width, max_height, dh)
                else:
                    factor = float(float(max_height) / float(sh))
                    w0 = int(sw * factor)
                    dw = (w0 - max_width) / 2
                    return w0, max_height, 'crop={0}:{1}:{2}:0'.format(max_width, max_height, dw)
            else:
                return int(sw*factor), max_height, None

        assert False, sizing_policy

    def parse_options(self, opt):
        super(VideoCodec, self).parse_options(opt)

        safe = self.safe_options(opt)

        if 'fps' in safe:
            f = safe['fps']
            if f < 1 or f > 120:
                del safe['fps']

        if 'bitrate' in safe:
            br = safe['bitrate']
            if br < 0.1 or br > 200:
                del safe['bitrate']

        if 'bufsize' in safe:
            bufsize = safe['bufsize']
            if bufsize < 1 or bufsize > 10000:
                del safe['bufsize']

        w = h = None

        if 'max_width' in safe:
            w = safe['max_width']
            if w < 16 or w > 4000:
                w = None
            elif w % 2:
                w += 1

        if 'max_height' in safe:
            h = safe['max_height']
            if h < 16 or h > 3000:
                h = None
            elif h % 2:
                h += 1

        crop_width, crop_height = None, None

        if 'crop' in safe:
            try:
                crop_width, crop_height, _, _ = safe['crop'].split(':')
                crop_width, crop_height = int(crop_width), int(crop_height)
            except:
                del safe['crop']
            else:
                if crop_width < 16 or crop_width > 3000:
                    crop_width = None
                if crop_height < 16 or crop_height > 3000:
                    crop_height = None

        if crop_width and crop_height:
            sw = crop_width
            sh = crop_height
        else:
            sw = safe.get('src_width', None)
            sh = safe.get('src_height', None)

        sizing_policy = 'Keep'
        if 'sizing_policy' in safe:
            if safe['sizing_policy'] in ['Fit', 'Fill', 'Stretch', 'Keep', 'ShrinkToFit', 'ShrinkToFill']:
                sizing_policy = safe['sizing_policy']

        w, h, filters = self._aspect_corrections(sw, sh, w, h, sizing_policy)
        w = self._div_by_2(w)
        h = self._div_by_2(h)

        safe['max_width'] = w
        safe['max_height'] = h
        safe['aspect_filters'] = filters

        # swap height and width if vertical rotate
        if safe.get('autorotate') and 'src_rotate' in safe:
            if safe['src_rotate'] in [90, 270]:
                old_w = w
                old_h = h
                safe['max_width'] = w = old_h
                safe['max_height'] = h = old_w

        if w and h:
            safe['aspect'] = '{0}:{1}'.format(w, h)

        safe = self._codec_specific_parse_options(safe)

        #w = safe['max_width']
        #h = safe['max_height']
        filters = safe['aspect_filters']

        # Use the most common pixel format by default. If the selected pixel format can not be selected,
        # ffmpeg select the best pixel format supported by the encoder.
        pix_fmt = safe.get('pix_fmt', 'yuv420p')

        optlist = ['-c:v', self.ffmpeg_codec_name, '-pix_fmt', pix_fmt]

        if 'fps' in safe:
            optlist.extend(['-r', str(round(safe['fps'], 2))])
        if 'bitrate' in safe:
            optlist.extend(['-vb', str(safe['bitrate']) + 'M'])
        if 'bufsize' in safe:
            optlist.extend(['-bufsize', str(safe['bufsize']) + 'k'])
        if w and h:
            optlist.extend(['-s', '{0}x{1}'.format(int(w), int(h))])
            if 'aspect' in safe:
                optlist.extend(['-aspect', '{0}:{1}'.format(int(w), int(h))])

        if safe.get('crop'):
            optlist = self._extend_vf(optlist, 'crop={0}'.format(safe['crop']))

        if filters:
            optlist = self._extend_vf(filters)

        if safe.get('autorotate', False) and 'src_rotate' in safe:
            rotate_filter = self._autorotate(safe['src_rotate'])
            optlist = self._extend_vf(optlist, rotate_filter)

        if 'filters' in safe:
            optlist = self._extend_vf(optlist, safe['filters'])

        optlist.extend(self._codec_specific_produce_ffmpeg_list(safe))
        return optlist


class AudioNullCodec(BaseCodec):
    """
    Null audio codec (no audio).
    """
    codec_name = None

    def parse_options(self, opt):
        return ['-an']


class VideoNullCodec(BaseCodec):
    """
    Null video codec (no video).
    """

    codec_name = None

    def parse_options(self, opt):
        return ['-vn']


class SubtitleNullCodec(BaseCodec):
    """
    Null video codec (no video).
    """

    codec_name = None

    def parse_options(self, opt):
        return ['-sn']

class DecoderNullCodec(BaseCodec):
    """
    Null video codec (no video).
    """

    codec_name = None

    def parse_options(self, opt):
        return []

class AudioCopyCodec(BaseCodec):
    """
    Copy audio stream directly from the source.
    """
    codec_name = 'copy'

    def parse_options(self, opt):
        return ['-c:a', 'copy']


class VideoCopyCodec(BaseCodec):
    """
    Copy video stream directly from the source.
    """
    codec_name = 'copy'

    def parse_options(self, opt):
        return ['-c:v', 'copy']


class SubtitleCopyCodec(BaseCodec):
    """
    Copy subtitle stream directly from the source.
    """
    codec_name = 'copy'

    def parse_options(self, opt):
        return ['-c:s', 'copy']


# Audio Codecs
class VorbisCodec(AudioCodec):
    """
    Vorbis audio codec.
    @see http://ffmpeg.org/trac/ffmpeg/wiki/TheoraVorbisEncodingGuide
    """
    codec_name = 'vorbis'
    ffmpeg_codec_name = 'libvorbis'
    encoder_options = AudioCodec.encoder_options.copy()
    encoder_options.update({
        'quality': int,  # audio quality. Range is 0-10(highest quality)
        # 3-6 is a good range to try. Default is 3
    })

    def _codec_specific_produce_ffmpeg_list(self, safe):
        optlist = []
        if 'quality' in safe:
            optlist.extend(['-qscale:a', safe['quality']])
        return optlist


class AacCodec(AudioCodec):
    """
    AAC audio codec.
    """
    codec_name = 'aac'
    ffmpeg_codec_name = 'aac'
    aac_experimental_enable = ['-strict', 'experimental']

    def _codec_specific_produce_ffmpeg_list(self, safe):
        return self.aac_experimental_enable


class FdkAacCodec(AudioCodec):
    """
    AAC audio codec.
    """
    codec_name = 'libfdk_aac'
    ffmpeg_codec_name = 'libfdk_aac'


class Ac3Codec(AudioCodec):
    """
    AC3 audio codec.
    """
    codec_name = 'ac3'
    ffmpeg_codec_name = 'ac3'


class FlacCodec(AudioCodec):
    """
    FLAC audio codec.
    """
    codec_name = 'flac'
    ffmpeg_codec_name = 'flac'


class DtsCodec(AudioCodec):
    """
    DTS audio codec.
    """
    codec_name = 'dts'
    ffmpeg_codec_name = 'dts'


class Mp3Codec(AudioCodec):
    """
    MP3 (MPEG layer 3) audio codec.
    """
    codec_name = 'mp3'
    ffmpeg_codec_name = 'libmp3lame'


class Mp2Codec(AudioCodec):
    """
    MP2 (MPEG layer 2) audio codec.
    """
    codec_name = 'mp2'
    ffmpeg_codec_name = 'mp2'


# Video Codecs
class TheoraCodec(VideoCodec):
    """
    Theora video codec.
    @see http://ffmpeg.org/trac/ffmpeg/wiki/TheoraVorbisEncodingGuide
    """
    codec_name = 'theora'
    ffmpeg_codec_name = 'libtheora'
    encoder_options = VideoCodec.encoder_options.copy()
    encoder_options.update({
        'quality': int,  # audio quality. Range is 0-10(highest quality)
        # 5-7 is a good range to try (default is 200k bitrate)
    })

    def _codec_specific_produce_ffmpeg_list(self, safe):
        optlist = []
        if 'quality' in safe:
            optlist.extend(['-qscale:v', safe['quality']])
        return optlist


class H264NvencCodec(VideoCodec):
    """
    H264/AVC Video codec by Nvidia.
    """
    codec_name = 'h264_nvenc'
    ffmpeg_codec_name = 'h264_nvenc'
    encoder_options = VideoCodec.encoder_options.copy()
    encoder_options.update({
        'preset': str,
        'profile': str,
        'level': str,
        'rc': str,
        'rc-lookahead': int,
        'surfaces': int,
        'cbr': bool,
        '2pass': bool,
        'gpu': int,
        'delay': int,
        'no-scenecut': bool,
        'forced-idr': bool,
        'b_adapt': bool,
        'spatial-aq': bool,
        'temporal-aq': bool,
        'zerolatency': bool,
        'nonref_p': bool,
        'strict_gop': bool,
        'aq-strength': bool,
        'cq': float,
        'qmin': float,
        'qmax': float
    })
    
    def _codec_specific_produce_ffmpeg_list(self, safe):
        optlist = []
        if 'preset' in safe:
            if safe['preset'] in ['default', 'slow', 'medium', 'fast', 'hp', 'hq', 'bd', 'll', 'llhq', 'llhp', 'lossless', 'losslesshp']:
                optlist.extend(['-preset', safe['preset']])
            else:
                logger.error(safe['preset']+' is not a valid preset for nvenc_h264 encoder ...')
                optlist.extend(['-preset', 'medium'])
        if 'profile' in safe:
            if safe['profile'] in ['baseline', 'main', 'high', 'high444p']:
                optlist.extend(['-profile:v', safe['profile']])
            else:
                logger.error(safe['profile']+' is not a valid profile for nvenc_h264 encoder ...')
                optlist.extend(['-profile:v', 'main'])
        if 'level' in safe:
            if safe['level'] in ['auto', '1', '1.0', '1b', '1.0b', '1.1', '1.2', '1.3', '2', '2.0', '2.1', '2.2', '3', '3.0', '3.1', '3.2', '4', '4.0', '4.1', '4.2', '5', '5.0', '5.1']:
                optlist.extend(['-level', safe['level']])
            else:
                logger.error(safe['level']+' is not a valid level for nvenc_h264 encoder ...')
                optlist.extend(['-level', 'auto'])
        if 'rc' in safe:
            if safe['rc'] in ['constqp', 'vbr', 'cbr', 'vbr_minqp', 'll_2pass_quality', 'll_2pass_size', 'vbr_2pass']:
                optlist.extend(['-rc', safe['rc']])
            else:
                logger.error(safe['rc']+' is not a valid rc for nvenc_h264 encoder ...')
                optlist.extend(['-rc', '-1'])
        if 'rc-lookahead' in safe:
            if safe['rc-lookahead'] >= -1:
                optlist.extend(['-rc-lookahead', str(safe['rc-lookahead'])])
            else:
                logger.error(str(safe['rc-lookahead'])+' is not a valid rc-lookahead for nvenc_h264 encoder ...')
                optlist.extend(['-rc-lookahead', '-1'])
        if 'surfaces' in safe:
            if safe['surfaces'] >= 0:
                optlist.extend(['-surfaces', str(safe['surfaces'])])
            else:
                logger.error(str(safe['surfaces'])+' is not a valid surfaces for nvenc_h264 encoder ...')
                optlist.extend(['-surfaces', '32'])
        if 'cbr' in safe:
            if type(safe['cbr']) == bool:
                optlist.extend(['-cbr', str(int(safe['cbr']))])
            else:
                logger.error(str(int(safe['cbr']))+' is not a valid cbr for nvenc_h264 encoder ...')
                optlist.extend(['-cbr', '0'])
        if '2pass' in safe:
            if type(safe['2pass']) == bool:
                optlist.extend(['-2pass', str(int(safe['2pass']))])
            else:
                logger.error(str(int(safe['2pass']))+' is not a valid 2pass for nvenc_h264 encoder ...')
                optlist.extend(['-2pass', 'auto'])
        if 'gpu' in safe:
            if safe['gpu'] >= -2:
                optlist.extend(['-gpu', str(safe['gpu'])])
            else:
                logger.error(str(safe['gpu'])+' is not a valid gpu for nvenc_h264 encoder ...')
                optlist.extend(['-gpu', 'any'])
        if 'delay' in safe:
            if safe['delay'] >= 0:
                optlist.extend(['-delay', str(safe['delay'])])
            else:
                logger.error(str(safe['delay'])+' is not a valid delay for nvenc_h264 encoder ...')
        if 'no-scenecut' in safe:
            if type(safe['no-scenecut']) == bool:
                optlist.extend(['-no-scenecut', str(int(safe['no-scenecut']))])
            else:
                logger.error(str(int(safe['no-scenecut']))+' is not a valid no-scenecut for nvenc_h264 encoder ...')
                optlist.extend(['-no-scenecut', '0'])
        if 'forced-idr' in safe:
            if type(safe['forced-idr']) == bool:
                optlist.extend(['-forced-idr', str(int(safe['forced-idr']))])
            else:
                logger.error(str(int(safe['forced-idr']))+' is not a valid forced-idr for nvenc_h264 encoder ...')
                optlist.extend(['-forced-idr', 'auto'])
        if 'b_adapt' in safe:
            if type(safe['b_adapt']) == bool:
                optlist.extend(['-b_adapt', str(int(safe['b_adapt']))])
            else:
                logger.error(str(int(safe['b_adapt']))+' is not a valid b_adapt for nvenc_h264 encoder ...')
                optlist.extend(['-b_adapt', '1'])
        if 'spatial-aq' in safe:
            if type(safe['spatial-aq']) == bool:
                optlist.extend(['-spatial-aq', str(int(safe['spatial-aq']))])
            else:
                logger.error(str(int(safe['spatial-aq']))+' is not a valid spatial-aq for nvenc_h264 encoder ...')
                optlist.extend(['-spatial-aq', '0'])
        if 'temporal-aq' in safe:
            if type(safe['temporal-aq']) == bool:
                optlist.extend(['-temporal-aq', str(int(safe['temporal-aq']))])
            else:
                logger.error(str(int(safe['temporal-aq']))+' is not a valid temporal-aq for nvenc_h264 encoder ...')
                optlist.extend(['-temporal-aq', '0'])
        if 'zerolatency' in safe:
            if type(safe['zerolatency']) == bool:
                optlist.extend(['-zerolatency', str(int(safe['zerolatency']))])
            else:
                logger.error(str(int(safe['zerolatency']))+' is not a valid zerolatency for nvenc_h264 encoder ...')
                optlist.extend(['-zerolatency', '0'])
        if 'nonref_p' in safe:
            if type(safe['nonref_p']) == bool:
                optlist.extend(['-nonref_p', str(int(safe['nonref_p']))])
            else:
                logger.error(str(int(safe['nonref_p']))+' is not a valid nonref_p for nvenc_h264 encoder ...')
                optlist.extend(['-nonref_p', '0'])
        if 'strict_gop' in safe:
            if type(safe['strict_gop']) == bool:
                optlist.extend(['-strict_gop', str(int(safe['strict_gop']))])
            else:
                logger.error(str(int(safe['strict_gop']))+' is not a valid strict_gop for nvenc_h264 encoder ...')
                optlist.extend(['-strict_gop', '0'])
        if 'aq-strength' in safe:
            if 1 <= safe['aq-strength'] <= 15:
                optlist.extend(['-aq-strength', str(safe['aq-strength'])])
            else:
                logger.error(str(safe['aq-strength'])+' is not a valid aq-strength for nvenc_h264 encoder ...')
                optlist.extend(['-aq-strength', '8'])
        if 'cq' in safe:
            if 0 <= safe['cq'] <= 51:
                optlist.extend(['-cq', str(safe['cq'])])
            else:
                logger.error(str(safe['cq'])+' is not a valid cq for hevc_nvenc encoder ...')
                optlist.extend(['-cq', '0'])
        if 'qmin' in safe:
            if 0 <= safe['qmin'] <= 51:
                optlist.extend(['-qmin', str(safe['qmin'])])
            else:
                logger.error(str(safe['qmin'])+' is not a valid qmin for hevc_nvenc encoder ...')
                optlist.extend(['-qmin', '0'])
        if 'qmax' in safe:
            if 0 <= safe['qmax'] <= 51:
                optlist.extend(['-qmax', str(safe['qmax'])])
            else:
                logger.error(str(safe['qmax'])+' is not a valid qmax for hevc_nvenc encoder ...')
                optlist.extend(['-qmax', '51'])
        return optlist

 
class HEVCNvencCodec(VideoCodec):
    """
    HEVC/AVC Video codec by Nvidia.
    """
    codec_name = 'hevc_nvenc'
    ffmpeg_codec_name = 'hevc_nvenc'
    encoder_options = VideoCodec.encoder_options.copy()
    encoder_options.update({
        'preset': str,
        'profile': str,
        'level': str,
        'tier': str,
        'rc': str,
        'rc-lookahead': int,
        'surfaces': int,
        'cbr': bool,
        '2pass': bool,
        'gpu': int,
        'delay': int,
        'no-scenecut': bool,
        'forced-idr': bool,
        'spatial_aq': bool,
        'temporal_aq': bool,
        'zerolatency': bool,
        'nonref_p': bool,
        'strict_gop': bool,
        'aq-strength': int,
        'cq': float,
        'qmin': float,
        'qmax': float
    })
    
    def _codec_specific_produce_ffmpeg_list(self, safe):
        optlist = []
        
        if 'preset' in safe:
            if safe['preset'] in ['default', 'slow', 'medium', 'fast', 'hp', 'hq', 'bd', 'll', 'llhq', 'llhp', 'lossless', 'losslesshp']:
                optlist.extend(['-preset', safe['preset']])
            else:
                logger.error(safe['preset']+' is not a valid preset for hevc_nvenc encoder ...')
                optlist.extend(['-preset', 'medium'])
        if 'profile' in safe:
            if safe['profile'] in ['main', 'main10', 'rext']:
                optlist.extend(['-profile:v', safe['profile']])
            else:
                logger.error(safe['profile']+' is not a valid profile for hevc_nvenc encoder ...')
                optlist.extend(['-profile:v', 'main'])
        if 'level' in safe:
            if safe['level'] in ['auto', '1', '1.0', '2', '2.0', '2.1', '3', '3.0', '3.1', '4', '4.0', '4.1', '5', '5.0', '5.1', '5.2', '6', '6.0', '6.1', '6.2']:
                optlist.extend(['-level', safe['level']])
            else:
                logger.error(safe['level']+' is not a valid level for hevc_nvenc encoder ...')
                optlist.extend(['-level', 'auto'])
        if 'tier' in safe:
            if safe['tier'] in ['main', 'high']:
                optlist.extend(['-tier', safe['tier']])
            else:
                logger.error(safe['tier']+' is not a valid tier for hevc_nvenc encoder ...')
                optlist.exntend(['-tier', 'main'])
        if 'rc' in safe:
            if safe['rc'] in ['constqp', 'vbr', 'cbr', 'vbr_minqp', 'll_2pass_quality', 'll_2pass_size', 'vbr_2pass']:
                optlist.extend(['-rc', safe['rc']])
            else:
                logger.error(safe['rc']+' is not a valid rc for hevc_nvenc encoder ...')
                optlist.extend(['-rc', '-1'])
        if 'rc-lookahead' in safe:
            if 0 < safe['rc-lookahead'] < 33:
                optlist.extend(['-rc-lookahead', str(safe['rc-lookahead'])])
            else:
                logger.error(safe['rc-lookahead']+' is not a valid rc-lookahead for hevc_nvenc encoder ...')
                optlist.extend(['-rc-lookahead', '-1'])
        if 'surfaces' in safe:
            if safe['surfaces'] >= 0:
                optlist.extend(['-surfaces', str(safe['surfaces'])])
            else:
                logger.error(safe['surfaces'+' is not a valid surfaces for hevc_nvenc encoder ...'])
                optlist.extend(['-surfaces', '32'])
        if 'cbr' in safe:
            if safe['cbr'] in [False, True]:
                optlist.extend(['-cbr', str(int(safe['cbr']))])
            else:
                logger.error(str(int(safe['cbr']))+' is not a valid cbr for hevc_nvenc encoder ...')
                optlist.extend(['-cbr', '0'])
        if '2pass' in safe:
            if safe['2pass'] in [False, True]:
                optlist.extend(['-2pass', str(int(safe['2pass']))])
            else:
                logger.error(str(int(safe['2pass']))+' is not a valid 2pass for hevc_nvenc encoder ...')
                optlist.extend(['-2pass', 'auto'])
        if 'gpu' in safe:
            if type(safe['gpu']) == int:
                optlist.extend(['-gpu', str(safe['gpu'])])
            else:
                logger.error(str('gpu')+' is not a valid gpu for hevc_nvenc encoder ...')
                optlist.extend(['-gpu', 'any'])
        if 'delay' in safe:
            if safe['delay'] >= 0:
                optlist.extend(['-delay', str(safe['delay'])])
            else:
                logger.error(str(safe['delay'])+' is not a valid delay for hevc_nvenc encoder ...')
        if 'no-scenecut' in safe:
            if safe['no-scenecut'] in [False, True]:
                optlist.extend(['-no-scenecut', str(int(safe['no-scenecut']))])
            else:
                logger.error(str(int(safe['no-scenecut']))+' is not a valid no-scenecut for hevc_nvenc encoder ...')
                optlist.extend(['-no-scenecut', '0'])
        if 'forced-idr' in safe:
            if safe['forced-idr'] in [False, True]:
                optlist.extend(['-forced-idr', str(int(safe['forced-idr']))])
            else:
                logger.error(str(int(safe['forced-idr']))+' is not a valid forced-idr for hevc_nvenc encoder ...')
                optlist.extend(['-forced-idr', 'auto'])
        if 'spatial_aq' in safe:
            if safe['spatial_aq'] in [False, True]:
                optlist.extend(['-spatial_aq', str(int(safe['spatial_aq']))])
            else:
                logger.error(str(int(safe['spatial_aq']))+' is not a valid spatial_aq for hevc_nvenc encoder ...')
                optlist.extend(['-spatial_aq', '0'])
        if 'temporal_aq' in safe:
            if safe['temporal_aq'] in [False, True]:
                optlist.extend(['-temporal_aq', str(int(safe['temporal_aq']))])
            else:
                logger.error(str(int(safe['temporal_aq']))+' is not a valid temporal_aq for hevc_nvenc encoder ...')
                optlist.extend(['-temporal_aq', '0'])
        if 'zerolatency' in safe:
            if safe['zerolatency'] in [False, True]:
                optlist.extend(['-zerolatency', str(int(safe['zerolatency']))])
            else:
                logger.error(str(int(safe['zerolatency']))+' is not a valid zerolatency for hevc_nvenc encoder ...')
                optlist.extend(['-zerolatency', '0'])
        if 'nonref_p' in safe:
            if safe['nonref_p'] in [False, True]:
                optlist.extend(['-nonref_p', str(int(safe['nonref_p']))])
            else:
                logger.error(str(int(safe['nonref_p']))+' is not a valid nonref_p for hevc_nvenc encoder ...')
                optlist.extend(['-nonref_p', '0'])
        if 'strict_gop' in safe:
            if safe['strict_gop'] in [False, True]:
                optlist.extend(['-strict_gop', str(int(safe['strict_gop']))])
            else:
                logger.error(str(int(safe['strict_gop']))+' is not a valid strict_gop for hevc_nvenc encoder ...')
                optlist.extend(['-strict_gop', '0'])
        if 'aq-strength' in safe:
            if 0 < safe['aq-strength'] < 16:
                optlist.extend(['-aq-strength', str(safe['aq-strength'])])
            else:
                logger.error(str(safe['aq-strength'])+' is not a valid aq-strength for hevc_nvenc encoder ...')
                optlist.extend(['-aq-strength', '8'])
        if 'cq' in safe:
            if 0 <= safe['cq'] <= 51:
                optlist.extend(['-cq', str(safe['cq'])])
            else:
                logger.error(str(safe['cq'])+' is not a valid cq for hevc_nvenc encoder ...')
                optlist.extend(['-cq', '0'])
        if 'qmin' in safe:
            if 0 <= safe['qmin'] <= 51:
                optlist.extend(['-qmin', str(safe['qmin'])])
            else:
                logger.error(str(safe['qmin'])+' is not a valid qmin for hevc_nvenc encoder ...')
                optlist.extend(['-qmin', '0'])
        if 'qmax' in safe:
            if 0 <= safe['qmax'] <= 51:
                optlist.extend(['-qmax', str(safe['qmax'])])
            else:
                logger.error(str(safe['qmax'])+' is not a valid qmax for hevc_nvenc encoder ...')
                optlist.extend(['-qmax', '51'])
        return optlist

class HEVCCodec(VideoCodec):
    """
    HEVC/AVC video codec.
    """
    codec_name = 'hevc'
    ffmpeg_codec_name = 'libx265'
    encoder_options = VideoCodec.encoder_options.copy()
    encoder_options.update({
        'preset': str,
        'tune': str,
        'ssim': bool,
        'psnr': bool,
        'profile': str,
        'level-idc': str,
        'high-tier': bool,
        'ref': int,
        'allow-non-conformance': bool,
        'uhd-bd': bool,
        'rd': int,
        'ctu': int,
        'min-cu-size': int,
        'limit-refs': int,
        'limit-modes': bool,
        'rect': bool,
        'amp': bool,
        'early-skip': bool,
        'rskip': bool,
        'fast-intra': bool,
        'b-intra': bool,
        'cu-lossless': bool,
        'tskip-fast': bool,
        'rd-refine': bool,
        'analysis-mode': int,
        'analysis-file': str,
        'rdoq-level': int,
        'tu-intra-depth': int,
        'tu-inter-depth': int,
        'limit-tu': int,
        'nr-intra': int,
        'nr-inter': int,
        'tskip': bool,
        'rdpenalty': int,
        'max-tu-size': int,
        'dynamic-rd': int,
        'ssim-rd': bool,
        'max-merge': int,
        'me': int,
        'subme': int,
        'merange': int,
        'temporal-mvp': bool,
        'weightp': bool,
        'weightb': bool,
        'analyze-src-pics': bool,
        'strong-intra-smoothing': bool,
        'constrained-intra': bool,
        'psy-rd': float,
        'psy-rdoq': float,
        'open-gop': bool,
        'keyint': int,
        'min-keyint': int,
        'scenecut': bool,
        'scenecut-bias': float,
        'intra-refresh': bool,
        'rc-lookahead': int,
        'lookahead-slices': int,
        'lookahead-threads': int,
        'b-adapt': int,
        'bframes': int,
        'bframe-bias': int,
        'b-pyramid': bool,
        'bitrate': int,
        'crf': float,
        'crf-max': float,
        'crf-min': float,
        'vbv-bufsize': int,
        'vbv-maxrate': int,
        'vbv-init': float,
        'qp': int,
        'lossless': bool,
        'aq-mode': int,
        'aq-strength': float,
        'aq-motion': bool,
        'qg-size': int,
        'cutree': bool,
        'pass': int,
        'stats': str,
        'slow-firstpass': bool,
        'multi-pass-opt-analysis': bool,
        'multi-pass-opt-distortion': bool,
        'strict-cbr': bool,
        'cbqpoffs': int,
        'crqpoffs': int,
        'qcomp': float,
        'qpstep': int,
        'qpmin': int,
        'qpmax': int,
        'rc-grain': bool,
        'qblur': float,
        'cplxblur': float,
        'signhide': bool,
        'qpfile': str,
        'scaling-list': str,
        'lambda-file': str,
        'sao': bool,
        'sao-non-deblock': bool,
        'sar': int,
        'display-window': str,
        'overscan': str,
        'videoformat': int,
        'range': str,
        'colorprim': int,
        'transfer': int,
        'colormatrix': int,
        'chromaloc': int,
        'hdr': bool,
        'hdr-opt': bool,
        'min-luma': int,
        'max-luma': int,
        'annexb': bool,
        'repeat-headers': bool,
        'aud': bool,
        'hrd': bool,
        'info': bool,
        'hash': int,
        'temporal-layers': bool,
        'log2-max-poc-lsb': int,
        'vui-timing-info': bool,
        'vui-hrd-info': bool,
        'opt-qp-pps': bool,
        'opt-ref-list-length-pps': bool,
        'multi-pass-opt-rps': bool,
        'opt-cu-delta-qp': bool
    })
    
    def check_condition(self, name, value, default, condition, x265_params):
        if condition:
            x265_params.append(name+'='+str(value))
        else:
            if type(default) != bool:
                x265_params.append(name+'='+str(default))
            logger.error(str(value)+' is not a valid '+name+' for libx265 encoder ...')
    
    def _codec_specific_produce_ffmpeg_list(self, safe):
        optlist = []
        x265_params = []
        if 'preset' in safe:
            if safe['preset'] in ['ultrafast', 'superfast', 'veryfast', 'faster', 'fast', 'medium', 'slow', 'slower', 'veryslow', 'placebo']:
                optlist.extend(['preset', safe['preset']])
            else:
                logger.error(safe['preset']+' is not a valid preset for libx265 encoder ...')
                optlist.extend(['preset', 'medium'])
        if 'tune' in safe:
            if safe['tune'] in ['psnr', 'ssim', 'grain', 'fastdecode', 'zerolatency']:
                optlist.extend(['tune', safe['tune']])
            else:
                logger.error(safe['tune']+' is not a valid tune for libx265 encoder ...')
                optlist.extend(['tune', 'grain'])
        if 'ssim' in safe: x265_params.append('ssim' if safe['ssim'] else 'no-ssim')
        if 'psnr' in safe: x265_params.append('psnr' if safe['psnr'] else 'no-psnr')
        if 'profile' in safe: self.check_condition('profile', safe['profile'], False, safe['profile'] in [ 'main', 'main-intra', 'mainstillpicture', 'main444-8', 'main444-intra', 'main444-stillpicture', 'main10', 'main10-intra', 'main422-10', 'main422-10-intra', 'main444-10', 'main444-10-intra', 'main12', 'main12-intra', 'main422-12', 'main422-12-intra', 'main444-12', 'main444-12-intra'], x265_params)
        if 'level-idc' in safe: self.check_condition('level-idc', safe['level-idc'], 0, safe['level-idc'] in ['1', '2', '2.1', '3', '3.1', '4', '4.1', '5', '5.1', '5.2', '6', '6.1', '6.2', '8.5'], x265_params)
        if 'high-tier' in safe: x265_params.append('high-tier' if safe['high-tier'] else 'no-high-tier')
        if 'ref' in safe: self.check_condition('ref', safe['ref'], 3, 1 <= safe['ref'] <= 16, x265_params)
        if 'allow-non-conformance' in safe: x265_params.append('allow-non-conformance' if safe['allow-non-conformance'] else 'no-allow-non-conformance')
        if 'uhd-bd' in safe: x265_params.append('uhd-bd' if safe['uhd-bd'] else 'no-uhd-bd')
        if 'rd' in safe: self.check_condition('rd', safe['rd'], 3, 1 <= safe['rd'] <= 6, x265_params)
        if 'ctu' in safe: self.check_condition('ctu', safe['ctu'], 64, safe['ctu'] in [64, 32, 16], x265_params)
        if 'min-cu-size' in safe: self.check_condition('min-cu-size', safe['min-cu-size'], 8, safe['min-cu-size'] in [8, 16, 32], x265_params)
        if 'limit-refs' in safe: self.check_condition('limit-refs', safe['limit-refs'], 3, 0 <= safe['limit-refs'] <= 3, x265_params)
        if 'limit-modes' in safe: x265_params.append('limit-modes' if safe['limit-modes'] else 'no-limit-modes')
        if 'rect' in safe: x265_params.append('rect' if safe['rect'] else 'no-rect')
        if 'amp' in safe: x265_params.append('amp' if safe['amp'] else 'no-amp')
        if 'early-skip' in safe: x265_params.append('early-skip' if safe['early-skip'] else 'no-early-skip')
        if 'rskip' in safe: x265_params.append('rskip' if safe['rskip'] else 'no-rskip')
        if 'fast-intra' in safe: x265_params.append('fast-intra' if safe['fast-intra'] else 'no-fast-intra')
        if 'b-intra' in safe: x265_params.append('b-intra' if safe['b-intra'] else 'no-b-intra')
        if 'cu-lossless' in safe: x265_params.append('cu-lossless' if safe['cu-lossless'] else 'no-cu-lossless')
        if 'tskip-fast' in safe: x265_params.append('tskip-fast' if safe['tskip-fast'] else 'no-tskip-fast')
        if 'rd-refine' in safe: x265_params.append('rd-refine' if safe['rd-refine'] else 'no-rd-refine')
        if 'analysis-mode' in safe: self.check_condition('analysis-mode', safe['analysis-mode'], False, 0 <= safe['analysis-mode'] <= 2, x265_params)
        if 'analysis-file' in safe: self.check_condition('analysis-file', safe['analysis-file'], False, True, x265_params)
        if 'rdoq-level' in safe:
            if safe['rdoq-level'] == -1: x265_params.append('no-rdoq-level')
            else: self.check_condition('rdoq-level', safe['rdoq-level'], False, 0 <= safe['rdoq-level'] <= 2, x265_params)
        if 'tu-intra-depth' in safe: self.check_condition('tu-intra-depth', safe['tu-intra-depth'], 1, 1 <= safe['tu-intra-depth'] <= 4, x265_params)
        if 'tu-inter-depth' in safe: self.check_condition('tu-inter-depth', safe['tu-inter-depth'], 1, 1 <= safe['tu-inter-depth'] <= 4, x265_params)
        if 'limit-tu' in safe: self.check_condition('limit-tu', safe['limit-tu'], 0, 0 <= safe['limit-tu'] <= 4, x265_params)
        if 'nr-intra' in safe: self.check_condition('nr-intra', safe['nr-intra'], 0, 0 <= safe['nr-intra'] <= 2000, x265_params)
        if 'nr-inter' in safe: self.check_condition('nr-inter', safe['nr-inter'], 0, 0 <= safe['nr-inter'] <= 2000, x265_params)
        if 'rdpenalty' in safe: self.check_condition('rdpenalty', safe['rdpenalty'], 0, 0 <= safe['rdpenalty'] <= 2, x265_params)
        if 'tskip' in safe: x265_params.append('tskip' if safe['tskip'] else 'no-tskip')
        if 'max-tu-size' in safe: self.check_condition('max-tu-size', safe['max-tu-size'], 32, safe['max-tu-size'] in [4,8,16,32], x265_params)
        if 'dynamic-rd' in safe: self.check_condition('dynamic-rd', safe['dynamic-rd'], 0, 0 <= safe['dynamic-rd'] <= 4, x265_params)
        if 'ssim-rd' in safe: x265_params.append('ssim-rd' if safe['ssim-rd'] else 'no-ssim-rd')
        if 'max-merge' in safe: self.check_condition('max-merge', safe['max-merge'], 2, 1 <= safe['max-merge'] <= 5, x265_params)
        if 'me' in safe: self.check_condition('me', safe['me'], 1, 0 <= safe['me'] <= 5, x265_params)
        if 'subme' in safe: self.check_condition('subme', safe['subme'], 2, 0 <= safe['subme'] <= 7, x265_params)
        if 'merange' in safe: self.check_condition('merange', safe['merange'], 57, 0 <= safe['merange'] <= 32768, x265_params)
        if 'temporal-mvp' in safe: x265_params.append('temporal-mvp' if safe['temporal-mvp'] else 'no-temporal-mvp')
        if 'weightp' in safe: x265_params.append('weightp' if safe['weightp'] else 'no-weightp')
        if 'weightb' in safe: x265_params.append('weightb' if safe['weightb'] else 'no-weightb')
        if 'analyze-src-pics' in safe: x265_params.append('analyze-src-pics' if safe['analyze-src-pics'] else 'no-analyze-src-pics')
        if 'strong-intra-smoothing' in safe: x265_params.append('strong-intra-smoothing' if safe['strong-intra-smoothing'] else 'no-strong-intra-smoothing')
        if 'constrained-intra' in safe: x265_params.append('constrained-intra' if safe['constrained-intra'] else 'no-constrained-intra')
        if 'psy-rd' in safe: self.check_condition('psy-rd', safe['psy-rd'], 2.0, 0.0 <= safe['psy-rd'] <= 5.0, x265_params)
        if 'psy-rdoq' in safe: self.check_condition('psy-rdoq', safe['psy-rdoq'], 0.0, 0.0 <= safe['psy-rdoq'] <= 50.0, x265_params)
        if 'open-gop' in safe: x265_params.append('open-gop' if safe['open-gop'] else 'no-open-gop')
        if 'keyint' in safe: self.check_condition('keyint', safe['keyint'], 250, True, x265_params)
        if 'min-keyint' in safe: self.check_condition('min-keyint', safe['min-keyint'], 0, 0 <= safe['min-keyint'], x265_params)
        if 'scenecut' in safe: x265_params.append('scenecut' if safe['scenecut'] else 'no-scenecut')
        if 'scenecut-bias' in safe: self.check_condition('scenecut-bias', safe['scenecut-bias'], 5.0, 0.0 <= safe['scenecut-bias'] <= 100.0, x265_params)
        if 'intra-refresh' in safe:
            if safe['intra-refresh']: x265_params.append('intra-refresh')
        if 'rc-lookahead' in safe: self.check_condition('rc-lookahead', safe['rc-lookahead'], 20, 0 < safe['rc-lookahead'] <= 250, x265_params)
        if 'lookahead-slices' in safe: self.check_condition('lookahead-slices', safe['lookahead-slices'], False, 0 <= safe['lookahead-slices'] <= 16, x265_params)
        if 'lookahead-threads' in safe: self.check_condition('lookahead-threads', safe['lookahead-threads'], 0, True, x265_params)
        if 'b-adapt' in safe: self.check_condition('b-adapt', safe['b-adapt'], 2, 0 <= safe['b-adapt'] <= 2, x265_params)
        if 'bframes' in safe: self.check_condition('bframes', safe['bframes'], 4, 0 <= safe['bframes'] <= 16, x265_params)
        if 'bframe-bias' in safe: self.check_condition('bframe-bias', safe['bframe-bias'], 0, -90 <= safe['bframe-bias'] <= 100, x265_params)
        if 'b-pyramid' in safe: x265_params.append('b-pyramid' if safe['b-pyramid'] else 'no-b-pyramid')
        if 'bitrate' in safe: self.check_condition('bitrate', safe['bitrate'], 0, 0 <= safe['bitrate'], x265_params)
        if 'crf' in safe: self.check_condition('crf', safe['crf'], 28.0, 0.0 <= safe['crf'] <= 51.0, x265_params)
        if 'crf-max' in safe: self.check_condition('crf-max', safe['crf-max'], False, 0 <= safe['crf-max'] <= 51.0, x265_params)
        if 'crf-min' in safe: self.check_condition('crf-min', safe['crf-min'], False, 0 <= safe['crf-min'] <= 51.0, x265_params)
        if 'vbv-bufsize' in safe: self.check_condition('vbv-bufsize', safe['vbv-bufsize'], 0, 0 <= safe['vbv-bufsize'], x265_params)
        if 'vbv-maxrate' in safe: self.check_condition('vbv-maxrate', safe['vbv-maxrate'], 0, 0 <= safe['vbv-maxrate'], x265_params)
        if 'vbv-init' in safe: self.check_condition('vbv-init', safe['vbv-init'], 0.9, 0.0 <= safe['vbv-init'] <= 1.0, x265_params)
        if 'qp' in safe: self.check_condition('qp', safe['qp'], False, 0 <= safe['qp'] <= 51, x265_params)
        if 'lossless' in safe: x265_params.append('lossless' if safe['lossless'] else 'no-lossless')
        if 'aq-mode' in safe: self.check_condition('aq-mode', safe['aq-mode'], 1, 0 <= safe['aq-mode'] <= 3, x265_params)
        if 'aq-strength' in safe: self.check_condition('aq-strength', safe['aq-strength'], 1.0, 0.0 <= safe['aq-strength'] <= 3.0, x265_params)
        if 'aq-motion' in safe: x265_params.append('aq-motion' if safe['aq-motion'] else 'no-aq-motion')
        if 'qg-size' in safe: self.check_condition('qg-size', safe['qg-size'], False, safe['qg-size'] in [8, 16, 32, 64], x265_params)
        if 'cutree' in safe: x265_params.append('cutree' if safe['cutree'] else 'no-cutree')
        if 'pass' in safe: self.check_condition('pass', safe['pass'], False, 0 <= safe['pass'] <= 3, x265_params)
        if 'stats' in safe: self.check_condition('stats', safe['stats'], False, True, x265_params)
        if 'slow-firstpass' in safe: x265_params.append('slow-firstpass' if safe['slow-firstpass'] else 'no-slow-firstpass')
        if 'multi-pass-opt-analysis' in safe: x265_params.append('multi-pass-opt-analysis' if safe['multi-pass-opt-analysis'] else 'no-multi-pass-opt-analysis')
        if 'multi-pass-opt-distortion' in safe: x265_params.append('multi-pass-opt-distortion' if safe['multi-pass-opt-distortion'] else 'no-multi-pass-opt-distortion')
        if 'strict-cbr' in safe: x265_params.append('strict-cbr' if safe['strict-cbr'] else 'no-strict-cbr')
        if 'cbqpoffs' in safe: self.check_condition('cbqpoffs', safe['cbqpoffs'], 0, -12 <= safe['cbqpoffs'] <= 12, x265_params)
        if 'crqpoffs' in safe: self.check_condition('crqpoffs', safe['crqpoffs'], 0, -12 <= safe['crqpoffs'] <= 12, x265_params)
        if 'qcomp' in safe: self.check_condition('qcomp', safe['qcomp'], 0.6, 0 <= safe['qcomp'] <= 1, x265_params)
        if 'qpstep' in safe: self.check_condition('qpstep', safe['qpstep'], 4, 0 <= safe['qpstep'], x265_params)
        if 'qpmin' in safe: self.check_condition('qpmin', safe['qpmin'], 0, 0 <= safe['qpmin'], x265_params)
        if 'qpmax' in safe: self.check_condition('qpmax', safe['qpmax'], 69, 0 <= safe['qpmax'], x265_params)
        if 'rc-grain' in safe: x265_params.append('rc-grain' if safe['rc-grain'] else 'no-rc-grain')
        if 'qblur' in safe: self.check_condition('qblur', safe['qblur'], 0.5, 0 <= safe['qblur'], x265_params)
        if 'cplxblur' in safe: self.check_condition('cplxblur', safe['cplxblur'], 20, 0 <= safe['cplxblur'], x265_params)
        if 'signhide' in safe: x265_params.append('signhide' if safe['signhide'] else 'no-signhide')
        if 'qpfile' in safe: self.check_condition('qpfile', safe['qpfile'], False, True, x265_params)
        if 'scaling-list' in safe: self.check_condition('scaling-list', safe['scaling-list'], False, True, x265_params)
        if 'lambda-file' in safe: self.check_condition('lambda-file', safe['lambda-file'], False, True, x265_params)
        if 'sao' in safe: x265_params.append('sao' if safe['sao'] else 'no-sao')
        if 'sao-non-deblock' in safe: x265_params.append('sao-non-deblock' if safe['sao-non-deblock'] else 'no-sao-non-deblock')
        if 'sar' in safe: self.check_condition('sar', safe['sar'], False, 1 <= safe['sar'] <= 16, x265_params)
        if 'display-window' in safe: self.check_condition('display-window', safe['display-window'], False, safe['display-window'] in ['left', 'top', 'right', 'bottom'], x265_params)
        if 'overscan' in safe: self.check_condition('overscan', safe['overscan'], False, safe['overscan'] in ['show', 'crop'], x265_params)
        if 'videoformat' in safe: self.check_condition('videoformat', safe['videoformat'], False, 0 <= safe['videoformat'] <= 5, x265_params)
        if 'range' in safe: self.check_condition('range', safe['range'], False, safe['range'] in ['full', 'limited'], x265_params)
        if 'colorprim' in safe: self.check_condition('colorprim', safe['colorprim'], False, 1 <= safe['colorprim'] <= 9, x265_params)
        if 'transfer' in safe: self.check_condition('transfer', safe['transfer'], False, 1 <= safe['transfer'] <= 18, x265_params)
        if 'colormatrix' in safe: self.check_condition('colormatrix', safe['colormatrix'], False, 0 <= safe['colormatrix'] <= 10, x265_params)
        if 'chromaloc' in safe: self.check_condition('chromaloc', safe['chromaloc'], False, 0 <= safe['chromaloc'] <= 5, x265_params)
        if 'hdr' in safe: x265_params.append('hdr' if safe['hdr'] else 'no-hdr')
        if 'hdr-opt' in safe: x265_params.append('hdr-opt' if safe['hdr-opt'] else 'no-hdr-opt')
        if 'min-luma' in safe: self.check_condition('min-luma', safe['min-luma'], False, 0 <= safe['min-luma'], x265_params)
        if 'max-luma' in safe: self.check_condition('max-luma', safe['max-luma'], False, 0 <= safe['max-luma'], x265_params)
        if 'annexb' in safe: x265_params.append('annexb' if safe['annexb'] else 'no-annexb')
        if 'repeat-headers' in safe: x265_params.append('repeat-headers' if safe['repeat-headers'] else 'no-repeat-headers')
        if 'aud' in safe: x265_params.append('aud' if safe['aud'] else 'no-aud')
        if 'hrd' in safe: x265_params.append('hrd' if safe['hrd'] else 'no-hrd')
        if 'info' in safe: x265_params.append('info' if safe['info'] else 'no-info')
        if 'hash' in safe: self.check_condition('hash', safe['hash'], False, 1 <= safe['hash'] <= 3, x265_params)
        if 'temporal-layers' in safe: x265_params('temporal-layers' if safe['temporal-layers'] else 'no-temporal-layers')
        if 'log2-max-poc-lsb' in safe: self.check_condition('log2-max-poc-lsb', safe['log2-max-poc-lsb'], 8, 0 <= safe['log2-max-poc-lsb'], x265_params)
        if 'vui-timing-info' in safe: x265_params.append('vui-timing-info' if safe['vui-timing-info'] else 'no-vui-timing-info')
        if 'vui-hrd-info' in safe: x265_params.append('vui-hrd-info' if safe['vui-hrd-info'] else 'no-vui-hrd-info')
        if 'opt-qp-pps' in safe: x265_params.append('opt-qp-pps' if safe['opt-qp-pps'] else 'no-opt-qp-pps')
        if 'opt-ref-list-length-pps' in safe: x265_params.append('opt-ref-list-length-pps' if safe['opt-ref-list-length-pps'] else 'no-opt-ref-list-length-pps')
        if 'multi-pass-opt-rps' in safe: x265_params.append('multi-pass-opt-rps' if safe['multi-pass-opt-rps'] else 'no-multi-pass-opt-rps')
        if 'opt-cu-delta-qp' in safe: x265_params.append('opt-cu-delta-qp' if safe['opt-cu-delta-qp'] else 'no-opt-cu-delta-qp')
        
        if len(x265_params) > 0:
            optlist.extend(['-x265-params', ':'.join(map(str,x265_params))])
        
        return optlist
class H264Codec(VideoCodec):
    """
    H.264/AVC video codec.
    @see http://ffmpeg.org/trac/ffmpeg/wiki/x264EncodingGuide
    """
    codec_name = 'h264'
    ffmpeg_codec_name = 'libx264'
    encoder_options = VideoCodec.encoder_options.copy()
    encoder_options.update({
        'preset': str,  # common presets are ultrafast, superfast, veryfast,
        # faster, fast, medium(default), slow, slower, veryslow
        'quality': int,  # constant rate factor, range:0(lossless)-51(worst)
        # default:23, recommended: 18-28
        # http://mewiki.project357.com/wiki/X264_Settings#profile
        'profile': str,  # default: not-set, for valid values see above link
        'tune': str,  # default: not-set, for valid values see above link
        'level': str,  # The H.264 level that you want to use for the output video
        'max_reference_frames': int,  # reference frames
        'max_rate': str,
        'max_frames_between_keyframes': int,
        'qmin': int,
        'qcomp': float,
        'keyint_min': int,
        'subq': int,
        'b-pyramid': int,
        'trellis': int,
    })

    def _codec_specific_produce_ffmpeg_list(self, safe):
        optlist = []
        if 'preset' in safe:
            optlist.extend(['-preset', safe['preset']])
        if 'quality' in safe:
            optlist.extend(['-crf', str(safe['quality'])])
        if 'profile' in safe:
            optlist.extend(['-profile:v', safe['profile']])
        if 'tune' in safe:
            optlist.extend(['-tune', safe['tune']])
        if 'level' in safe:
            optlist.extend(['-level', safe['level']])
        if 'max_reference_frames' in safe:
            optlist.extend(['-refs', str(safe['max_reference_frames'])])
        if 'max_rate' in safe:
            optlist.extend(['-maxrate', str(safe['max_rate'])])
        if 'max_frames_between_keyframes' in safe:
            optlist.extend(['-g', str(safe['max_frames_between_keyframes'])])
        if 'qmin' in safe:
            optlist.extend(['-qmin', str(safe['qmin'])])
        if 'qcomp' in safe:
            optlist.extend(['-qcomp', str(safe['qcomp'])])
        if 'keyint_min' in safe:
            optlist.extend(['-keyint_min', str(safe['keyint_min'])])
        if 'subq' in safe:
            optlist.extend(['-subq', str(safe['subq'])])
        if 'b-pyramid' in safe:
            optlist.extend(['-b-pyramid', str(safe['b-pyramid'])])
        if 'trellis' in safe:
            optlist.extend(['-trellis', str(safe['trellis'])])

        return optlist


class DivxCodec(VideoCodec):
    """
    DivX video codec.
    """
    codec_name = 'divx'
    ffmpeg_codec_name = 'mpeg4'


class Vp8Codec(VideoCodec):
    """
    Google VP8 video codec.
    """
    codec_name = 'vp8'
    ffmpeg_codec_name = 'libvpx'


class H263Codec(VideoCodec):
    """
    H.263 video codec.
    """
    codec_name = 'h263'
    ffmpeg_codec_name = 'h263'


class FlvCodec(VideoCodec):
    """
    Flash Video codec.
    """
    codec_name = 'flv'
    ffmpeg_codec_name = 'flv'


class Ffv1Codec(VideoCodec):
    """
    FFV1 Video codec.
    """
    codec_name = 'ffv1'
    ffmpeg_codec_name = 'ffv1'
    encoder_options = VideoCodec.encoder_options.copy()
    encoder_options.update({
        'level': int,  # 1, 3. Select which FFV1 version to use.
        'coder': int,  # 0=Golomb-Rice, 1=Range Coder,
                       # 2=Range Coder(with custom state transition table)
        'context': int,  # 0=small, 1=large
        'g': int,  # GOP size, >= 1. For archival use, GOP-size should be "1".
        'slices': int,  # 4, 6, 9, 12, 16, 24, 30.
                        # Each frame is split into this number of slices.
                        # This affects multithreading performance, as well as filesize:
                        # Increasing the number of slices might speed up
                        # performance, but also increases the filesize.
        'slicecrc': int,  # Error correction/detection, 0=off, 1=on.
                          # Enabling this option adds CRC information to each slice.
                          # This makes it possible for a decoder to detect
                          # errors in the bitstream, rather than blindly
                          # decoding a broken slice.
    })

    def _codec_specific_produce_ffmpeg_list(self, safe):
        optlist = []
        if 'level' in safe:
            optlist.extend(['-level', str(safe['level'])])
        if 'coder' in safe:
            optlist.extend(['-coder', str(safe['coder'])])
        if 'context' in safe:
            optlist.extend(['-context', str(safe['context'])])
        if 'g' in safe:
            optlist.extend(['-g', str(safe['g'])])
        if 'slices' in safe:
            optlist.extend(['-slices', str(safe['slices'])])
        if 'slicecrc' in safe:
            optlist.extend(['-slicecrc', str(safe['slicecrc'])])

        return optlist


class MpegCodec(VideoCodec):
    """
    Base MPEG video codec.
    """
    # Workaround for a bug in ffmpeg in which aspect ratio
    # is not correctly preserved, so we have to set it
    # again in vf; take care to put it *before* crop/pad, so
    # it uses the same adjusted dimensions as the codec itself
    # (pad/crop will adjust it further if neccessary)
    def _codec_specific_parse_options(self, safe):
        w = safe['max_width']
        h = safe['max_height']

        if w and h:
            filters = safe['aspect_filters']
            tmp = 'aspect=%d:%d' % (w, h)

            if filters is None:
                safe['aspect_filters'] = tmp
            else:
                safe['aspect_filters'] = tmp + ',' + filters

        return safe


class Mpeg1Codec(MpegCodec):
    """
    MPEG-1 video codec.
    """
    codec_name = 'mpeg1'
    ffmpeg_codec_name = 'mpeg1video'


class Mpeg2Codec(MpegCodec):
    """
    MPEG-2 video codec.
    """
    codec_name = 'mpeg2'
    ffmpeg_codec_name = 'mpeg2video'


# Subtitle Codecs
class MOVTextCodec(SubtitleCodec):
    """
    mov_text subtitle codec.
    """
    codec_name = 'mov_text'
    ffmpeg_codec_name = 'mov_text'


class SSA(SubtitleCodec):
    """
    SSA (SubStation Alpha) subtitle.
    """
    codec_name = 'ass'
    ffmpeg_codec_name = 'ass'


class SubRip(SubtitleCodec):
    """
    SubRip subtitle.
    """
    codec_name = 'subrip'
    ffmpeg_codec_name = 'subrip'


class DVBSub(SubtitleCodec):
    """
    DVB subtitles.
    """
    codec_name = 'dvbsub'
    ffmpeg_codec_name = 'dvbsub'


class DVDSub(SubtitleCodec):
    """
    DVD subtitles.
    """
    codec_name = 'dvdsub'
    ffmpeg_codec_name = 'dvdsub'

class H263CuvidCodec(DecoderCodec):
    """
    H263 cuda decoder
    """
    codec_name = 'h263_cuvid'
    ffmpeg_codec_name = 'h263_cuvid'
    
class H264CuvidCodec(DecoderCodec):
    """
    H264 cuda decoder
    """
    codec_name = 'h264_cuvid'
    ffmpeg_codec_name = 'h264_cuvid'

class HEVCCuvidCodec(DecoderCodec):
    """
    HEVC cuda decoder
    """
    codec_name = 'hevc_cuvid'
    ffmpeg_codec_name = 'hevc_cuvid'

class MJPEGCuvidCodec(DecoderCodec):
    """
    MJPEG cuda decoder
    """
    codec_name = 'mjpeg_cuvid'
    ffmpeg_codec_name = 'mjpeg_cuvid'
    
class Mpeg1CuvidCodec(DecoderCodec):
    """
    MPEG1 cuda decoder
    """
    codec_name = 'mpeg1_cuvid'
    ffmpeg_codec_name = 'mpeg1_cuvid'

class Mpeg2CuvidCodec(DecoderCodec):
    """
    MPEG2 cuda decoder
    """
    codec_name = 'mpeg2_cuvid'
    ffmpeg_codec_name = 'mpeg2_cuvid'

class Mpeg4CuvidCodec(DecoderCodec):
    """
    MPEG4 cuda decoder
    """
    codec_name = 'mpeg4_cuvid'
    ffmpeg_codec_name = 'mpeg4_cuvid'

class Vc1CuvidCodec(DecoderCodec):
    """
    VC1 cuda decoder
    """
    codec_name = 'vc1_cuvid'
    ffmpeg_codec_name = 'vc1_cuvid'
    
class Vp8CuvidCodec(DecoderCodec):
    """
    VP8 cuda decoder
    """
    codec_name = 'vp8_cuvid'
    ffmpeg_codec_name = 'vp8_cuvid'
    
class Vp9CuvidCodec(DecoderCodec):
    """
    VP9 cuda decoder
    """
    codec_name = 'vp9_cuvid'
    ffmpeg_codec_name = 'vp9_cuvid'
        
audio_codec_list = [
    AudioNullCodec, AudioCopyCodec, VorbisCodec, AacCodec, Mp3Codec, Mp2Codec,
    FdkAacCodec, Ac3Codec, DtsCodec, FlacCodec
]

decoder_codec_list = [
    DecoderNullCodec, H263CuvidCodec, H264CuvidCodec, HEVCCuvidCodec, MJPEGCuvidCodec,
    Mpeg1CuvidCodec, Mpeg2CuvidCodec, Mpeg4CuvidCodec, Vc1CuvidCodec,
    Vp8CuvidCodec, Vp9CuvidCodec
]

video_codec_list = [
    VideoNullCodec, VideoCopyCodec, TheoraCodec, H264Codec,
    DivxCodec, Vp8Codec, H263Codec, FlvCodec, Ffv1Codec, Mpeg1Codec,
    Mpeg2Codec, HEVCNvencCodec, H264NvencCodec, HEVCCodec
]

subtitle_codec_list = [
    SubtitleNullCodec, SubtitleCopyCodec, MOVTextCodec, SSA, SubRip, DVDSub,
    DVBSub
]
