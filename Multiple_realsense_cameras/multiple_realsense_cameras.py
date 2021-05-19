#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__author__ = "Ivo Marvan"
__email__ = "ivo@marvan.cz"
__description__ = '''
    Experiments with multiple D415, T265 cameras.
'''
import sys
import os
import io
import pyrealsense2 as rs
import cv2
import numpy as np
from pprint import pprint
try:
    from PIL import ImageFont, ImageDraw, Image
except ModuleNotFoundError:
    from willow import ImageFont, ImageDraw, Image

# fot nice text data interpretation 
import tableprint

# for TTFontSource
import tempfile
import requests

# --- Realsence problem core -------------------------------------------------------------------------------------------
class RealsenseCamera:
    '''
    Abstraction of any RealsenseCamera
    '''
    __colorizer = rs.colorizer()

    def __init__(
        self,
        serial_number :str,
        name: str
    ):
        self.__serial_number = serial_number
        self.__name = name
        self.__pipeline = None
        self.__started = False
        self.__start_pipeline()

    def __del__(self):
        if self.__started and not self.__pipeline is None:
            self.__pipeline.stop()
            
    def get_full_name(self):
        return f'{self.__name} ({self.__serial_number})'

    def __start_pipeline(self):
        # Configure depth and color streams
        self.__pipeline = rs.pipeline()
        config = rs.config()
        config.enable_device(self.__serial_number)
        self.__pipeline.start(config)
        self.__started = True
        print(f'{self.get_full_name()} camera is ready.')

    def get_frames(self) -> [rs.frame]:
        '''
        Return a frame do not care about type
        '''
        frameset = self.__pipeline.wait_for_frames()
        if frameset:
            return [f for f in frameset]
        else:
            return []

    @classmethod
    def get_title(cls, frame: rs.frame, whole: bool) -> str:
        # <pyrealsense2.video_stream_profile: Fisheye(2) 848x800 @ 30fps Y8>
        profile_str = str(frame.profile)
        first_space_pos = profile_str.find(' ')
        whole_title = profile_str[first_space_pos + 1: -1]
        if whole:
            return whole_title
        return whole_title.split(' ')[0]


    @classmethod
    def get_images_from_video_frames(cls, frames: [rs.frame]) -> ([(np.ndarray, rs.frame)] , [rs.frame], int, int):
        '''
        From all the frames, it selects those that can be easily interpreted as pictures.
        Converts them to images and finds the maximum width and maximum height from all of them.
        '''
        max_width = -1
        max_height = -1
        img_frame_tuples = []
        unused_frames = []
        for frame in frames:
            if frame.is_video_frame():
                if frame.is_depth_frame():
                    img = np.asanyarray(RealsenseCamera.__colorizer.process(frame).get_data())
                else:
                    img = np.asanyarray(frame.get_data())
                    img = img[...,::-1].copy()  # RGB<->BGR
                max_height = max(max_height, img.shape[0])
                max_width  = max(max_width, img.shape[1])
                img_frame_tuples.append((img,frame))
            else:
                unused_frames.append(frame)
        return img_frame_tuples, unused_frames, max_width, max_height

    @classmethod
    def get_table_from_text_data_frame(cls, frame: rs.frame, round_ndigits: int = 2, int_len: int = 3) -> (list, rs.frame):
        '''
        Returns list of rows which ase ists of columns.
        Result can be interpreted as table.
        First row is a header.

        @TODO add interpreatation of other than T265 and D415 camera. (I do not have it)
        '''
        title = RealsenseCamera.get_title(frame, whole=False)
        if frame.is_motion_frame():
            motion_data = frame.as_motion_frame().get_motion_data()
            table = [
                ['name', 'x', 'y', 'z'],
                [title, round(motion_data.x, 2), round(motion_data.y, 2), round(motion_data.z, 2)]
            ]
        elif frame.is_pose_frame():
            data = frame.as_pose_frame().get_pose_data()
            table= [
                [title, 'x', 'y', 'z', 'w'],
                ['acceleration', data.acceleration.x, data.acceleration.y, data.acceleration.z, ''],
                ['angular_acceleration', data.angular_acceleration.x, data.angular_acceleration.y,
                 data.angular_acceleration.z, ''],
                ['angular_velocity', data.angular_velocity.x, data.angular_velocity.y, data.angular_velocity.z, ''],
                ['rotation', data.rotation.x, data.rotation.y, data.rotation.z, data.rotation.w],
                ['translation', data.translation.x, data.translation.y, data.translation.z, ''],
                ['velocity', data.velocity.x, data.velocity.y, data.velocity.z, ''],
                ['mapper_confidence', data.mapper_confidence, '', '', ''],
                ['tracker_confidence', data.tracker_confidence, '', '', ''],
            ]
        else:
            sys.stderr.write(f'No frame to date/image convertor for {frame}.\n')
            return [], None
        if not round_ndigits is None:
            # tabled data to formated strings
            for i, row in enumerate(table):
                for j, cell in enumerate(row):
                    if isinstance(cell, float):
                        formated_str = f'{round(cell, round_ndigits):{round_ndigits + 3}.{round_ndigits}}'
                    elif isinstance(cell, int):
                        formated_str = f'{cell:{int_len}}'
                    else:
                        formated_str = str(cell)
                    table[i][j] = formated_str
        return table, frame

# --- GUI --------------------------------------------------------------------------------------------------------------
class TTFontSource:

    URLS = [
        'https://github.com/bluescan/proggyfonts/blob/master/ProggyCrossed/ProggyCrossed%20Regular.ttf?raw=true',
        'https://github.com/bluescan/proggyfonts/blob/master/ProggyVector/ProggyVector%20Regular%20Mac.ttf?raw=true'
    ]

    __size_casched_fonts = {}  # fonts strorage for size as key

    @classmethod
    def __get_font_from_url(cls, url: str):
        '''
        Returns font data from url.

        The results is casched to file in the tmp directory.
        '''
        cache_path = cls.__url_to_path(url)
        if os.path.isfile(cache_path):
            with open(cache_path, 'rb') as f:
                return io.BytesIO(f.read())
        try:
            response = requests.get(url)
            content = response.content
        except Exception as e:
            sys.stderr.write(f'{cls.__class__.__name__}: {e}, url="{url}"\n')
            content = None
        with open(cache_path, 'wb') as f:
            return f.write(content)
        return io.BytesIO(content)

    @classmethod
    def __url_to_path(cls, url: str, expected_extension: str = 'ttf') -> str:
        filename = url + '.' + expected_extension
        filename = filename.replace('/', '_').replace('&', '\&')
        return os.path.join(tempfile.gettempdir(), filename)

    @classmethod
    def get_font(cls, size: int = 15):
        try:
            return cls.__size_casched_fonts[size]
        except KeyError:
            for url in cls.URLS:
                font = cls.__get_font_from_url(url)
                try:
                    font = ImageFont.truetype(font, size)
                    cls.__size_casched_fonts[size] = font
                    return font
                except Exception as e:
                    sys.stderr.write(f'{cls.__class__.__name__}.: {e}, url="{url}"\n')
            return None


class ImgWindow:
    '''
    Window from OpenCv for showing the result [in the loop].
    '''
    def __init__(self, name: str = 'ImgWindow', type: int = cv2.WINDOW_NORMAL):
        self._name = name
        cv2.namedWindow(self._name, type)

    def swow(self, img_array: np.ndarray) -> bool:
        if img_array is None:
            return True
        cv2.imshow(self._name, img_array)
        return True

    def is_stopped(self) -> bool:
        key = cv2.waitKey(1)
        if key == ord('q') or key == 27:
            return True
        return cv2.getWindowProperty(self._name, cv2.WND_PROP_VISIBLE) < 1

class RealsenseFramesToImage:
    '''
    Take all frames in one moment and interpret them as one image. 
    
    - Starts with the interpretation of each frame to separate the image. 
    - Connects all images together.
    '''
    def __init__(self):
        self.__casched_fonts = {}


    def get_image_from_frames(self, frames: [rs.frame], add_tile: bool = True) -> np.array:
        # 'image' kind of frames
        img_frame_tuples, unsed_frames, max_width, max_height = RealsenseCamera.get_images_from_video_frames(frames)
        if add_tile:
            images, max_height = self.__add_titles(img_frame_tuples, max_height)
        else:
            images = [img_frame[0] for img_frame in img_frame_tuples]
        # 'data' or 'tex' kind of frames
        images_from_text_frames = self.__images_from_text_frames(unsed_frames, max_width, max_height)
        # together
        images += images_from_text_frames
        if len(images) > 0:
            # concat all to one image
            ret_img = self.__concat_images(images, max_width, max_height)
        else:
            # placeholder for no frames (no images)
            ret_img = np.zeros(shape=(800, 600, 3))
        return ret_img

    def __images_from_text_frames(self, frames: [rs.frame], width:int, height: int) -> [np.ndarray]:
        return [
            self.__from_lines_to_img(
                self.__from_tabled_data_to_str(
                    RealsenseCamera.get_table_from_text_data_frame(frame)
                ),
                width,
                height)
            for frame in frames
        ]

    def __from_tabled_data_to_str(self, table_frame_tuple: ([[str]], rs.frame)) -> str:
        table, frame = table_frame_tuple
        max_columns_len = []
        for r, row in enumerate(table):
            for c, cell in enumerate(row):
                if r==0:  # first row
                    max_columns_len.append(len(cell))
                else:
                    max_columns_len[c] = max(max_columns_len[c], len(cell))
        str_io = io.StringIO('')
        tableprint.table(table[1:], table[0], width=max_columns_len, out=str_io, style='round')
        title = ' '*3 + RealsenseCamera.get_title(frame, whole=True)
        table_str = str_io.getvalue()
        return title + '\n' + table_str

    def __add_titles(
        self,
        img_frm_tuples: [(np.ndarray, rs.frame)],
        max_height:int,
        default_height: int = 40,
        default_font_size: int = 28,
        bacground_color = (255, 255, 255),
        color = (0, 0, 0),
        dx: int = 10,
        dy: int = 10
    ) -> ([np.ndarray], int):
        ret_images = []
        font = TTFontSource.get_font(size=default_font_size)
        for img, frame in img_frm_tuples:
            title = RealsenseCamera.get_title(frame, whole=True)
            if len(img.shape) > 2:
                rgb = True
                height, width, _ = img.shape
                title_img = Image.new('RGB', (width, default_height), color=bacground_color)
            else:
                rgb = False
                height, width = img.shape
                r, g, b = bacground_color
                intcolor = (b << 16) | (g << 8) | r
                title_img = Image.new('RGB', (width, default_height), color=intcolor)

            draw = ImageDraw.Draw(title_img)
            draw.text((dx, dy), title, font=font, fill=color)
            title_img = np.array(title_img)
            if not rgb:
                title_img = title_img[:,:,0]
            ret_images.append(np.vstack((title_img, img)))
        return ret_images, max_height + default_height

    def __from_lines_to_img(
        self,
        text: [str],
        width: int,
        height: int,
        bacground_color = (255,255,255),
        color=(0, 0, 0),
        dx : int = 10,
        dy : int = 10
    ) -> np.ndarray:
        '''
        Create an image of a given width height, where the text with a known number of lines (of the same length) will be large enough.
        '''
        rows = text.splitlines()
        # rows had Title and table rows[1] is first row of table
        font = self.__get_font_with_good_size(rows[1], width, dx)
        img = Image.new('RGB', (width, height), color=bacground_color)
        draw = ImageDraw.Draw(img)
        draw.text((dx, dy), text, font=font, fill=color)
        # for i, row in enumerate(text):
        #     draw.text((10, 20 * i), row, font=font, fill=color)
        return np.array(img)

    def __get_font_with_good_size(self, first_row: str, width:int, dx: int):
        l = len(first_row)
        try:
            return self.__casched_fonts[l]
        except KeyError:
            font_size = 10  # starting font size
            font = TTFontSource.get_font(size=font_size)
            width_dx = width - 2 * dx
            while font.getsize(first_row)[0] < width_dx:
                # iterate until the text size is just larger than the criteria
                font_size += 1
                font = TTFontSource.get_font(size=font_size)
            # de-increment to be sure it is less than criteria
            font_size -= 2
            font = TTFontSource.get_font(size=font_size)
            self.__casched_fonts[l] = font
            return font

    def __concat_images(
        self,
        images: [np.array],
        max_width: int,
        max_height: int,
        max_columns: int = 4,
        bacground_color=(255,255,255)
    ) -> np.array:
        # diferent images in the set, transform all to RGB
        images = [cv2.cvtColor(img,cv2.COLOR_GRAY2RGB) if len(img.shape) < 3 else img for img in images]
        # reshape to the same size max_width x max_height
        images = [self.__enlarge_img_by_add_background(img, max_width, max_height, bacground_color) for img in images]
        # divide images to rows and columns
        images = [images[i:i + max_columns] for i in range(0, len(images), max_columns)]
        for row_index, rows_images in enumerate(images):
            # concat images in one rows
            for col_index, img in enumerate(rows_images):
                if col_index == 0:
                    # first one
                    col_img = img
                else:
                    col_img = np.hstack((col_img, img))
            # add placeholder to shor column
            for i in range(max_columns - len(rows_images)):
                placeholder_img = np.zeros((max_height, max_width, 3), np.uint8)
                placeholder_img[:, :] = bacground_color
                col_img = np.hstack((col_img, placeholder_img))
            # concat rows to one image
            if row_index == 0:
                # first one
                ret_img = col_img
            else:
                ret_img = np.vstack((ret_img, col_img))
        return ret_img

    def __enlarge_img_by_add_background(
        self, img: np.ndarray, enlarge_width: int, enlarge_height: int,
        bacground_color = (255,255,255)
    ) -> np.ndarray:
        width, height = img.shape[1], img.shape[0]
        if width >= enlarge_width and height >= enlarge_height:
            # good enough
            return img
        new_img = np.zeros((enlarge_height,enlarge_width,3), np.uint8)
        new_img[:,:] = bacground_color
        x = int((enlarge_width - width) / 2)
        y = int((enlarge_height - height) / 2)
        new_img[y:y+height, x:x+width] = img
        return new_img



class AllCamerasLoop:
    '''
    Take info from all conected cameras in the loop.
    '''

    @classmethod
    def get_conected_cameras_info(cls, camera_name_suffix: str = 'T265') -> [(str, str)]:
        '''
        Return list of (serial number,names) conected devices.
        Eventualy only fit given suffix (like T265, D415, ...)
        (based on https://github.com/IntelRealSense/librealsense/issues/2332)
        '''
        ret_list = []
        ctx = rs.context()
        for d in ctx.devices:
            serial_number = d.get_info(rs.camera_info.serial_number)
            name = d.get_info(rs.camera_info.name)
            if camera_name_suffix and not name.endswith(camera_name_suffix):
                continue
            ret_list.append((serial_number, name))
        return ret_list

    @classmethod
    def get_all_conected_cameras(cls) -> [RealsenseCamera]:
        cameras = cls.get_conected_cameras_info(camera_name_suffix=None)
        return [RealsenseCamera(serial_number, name) for serial_number, name in cameras]

    def __init__(self):
        self.__cameras = self.get_all_conected_cameras()
        self.__frames_interpreter = RealsenseFramesToImage()

    def get_frames(self) -> [rs.frame]:
        '''
        Return frames in given order. 
        '''
        ret_frames = []

        for camera in self.__cameras:
            frames = camera.get_frames()
            if frames:
                ret_frames += frames
        return ret_frames


    def __get_window_name(self):
        s = ''
        for camera in self.__cameras:
            if s:
                s += ', '
            s += camera.get_full_name()
        return s

    def run_loop(self):
        stop = False
        window = ImgWindow(name=self.__get_window_name())
        while not stop:
            frames = self.get_frames()
            window.swow(self.__frames_interpreter.get_image_from_frames(frames))
            stop = window.is_stopped()


if __name__ == "__main__":
    viewer = AllCamerasLoop()
    viewer.run_loop()





