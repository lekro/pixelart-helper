from PIL import Image, ImageTk
import numpy as np
import os, re, gc, sys
import logging

# Try to get cKDTree from scipy.
found_ckdtree = False
try:
    from scipy.spatial import cKDTree
    found_ckdtree = True
except ImportError:
    pass

# Dictionary of interpolation strings to 
# PIL interpolation enumeration values
interpval = dict(nearest=Image.NEAREST,
                 bilinear=Image.BILINEAR,
                 bicubic=Image.BICUBIC,
                 lanczos=Image.LANCZOS)

class PixelartProcessor:

    def __init__(self, textures_path, image_path, output_path,
            colorspace='RGB', interp='lanczos', minkowski=2,
            image_scaling=None, texture_dimension=None,
            logging_handler=None):

        self.textures_path = textures_path
        self.image_path = image_path
        self.output_path = output_path
        self.colorspace = colorspace
        self.interp = interpval[interp]
        self.minkowski = minkowski
        self.image_scaling = image_scaling
        self.texture_dimension = texture_dimension
        
        # Set up logging.
        self.logger = logging.getLogger(__name__)
        if logging_handler is None:
            self.logger.addHandler(logging.NullHandler())
        else:
            self.logger.addHandler(logging_handler)

    def is_output_path_valid(self):

        # Make sure the output path is not None or a directory
        if self.output_path is None or os.path.isdir(self.output_path):
            self.logger.critical("Invalid output path!")
            return False
        try:
            Image.fromarray(np.array([[[0,0,0]]], 
                            dtype='uint8')).save(self.output_path)
            return True
        except ValueError as e:
            self.logger.critical("Invalid output format! (%s)" % e)
            return False

    def load_textures(self):

        self.colors = {}
        self.textures = {}

        if self.textures_path is None or not os.path.isdir(self.textures_path):
            self.logger.critical("Invalid texture path!")
            return False
        for fi in os.listdir(self.textures_path):
            # TODO Perform filtering on names of files
            # TODO Get name of texture from file name

            try:
                texture = Image.open(os.path.join(self.textures_path, fi))
            except ValueError:
                continue

            # Now we know this is a valid texture.
            # Check to make sure its shape matches the expected shape, if any.
            if texture_dimension is not None:
                if not texture.size == self.texture_dimension:
                    continue
            
            # Resize to 1x1 using desired interpolation method, then
            # get the only pixel in the image to find the average color.
            # We also convert to the desired color space.
            self.colors[name] = np.array(texture.resize((1,1),
                resample=self.interp).convert(self.colorspace)\
                        .getpixel((0,0)))
            self.pics[name] = texture

        if len(self.colors) == 0:
            self.logger.critical("No loadable textures found!")
            return False
        return True

    def load_image(self):

        if self.input_path is None or not os.path.isfile(self.input_path):
            self.logger.critical("Invalid image path!")
            return False

        self.image = None
        try:
            self.image = Image.open(self.image_path)
        except IOError as e:
            self.logger.critical("Couldn't load image! (%s)" % e)
            return False
        except ValueError as e:
            self.logger.critical("Unknown image format! (%s)" % e)
            return False

        # Scale if necessary
        if self.input_scaling is not None:
            self.image = self.image.resize(self.image_scaling,
                    resample=self.interp)

    def find_nearest_neighbors(self):

        # Find nearest neighbors here.
        vals = np.array(list(self.colors.values()))

        # Make a cKDTree if we have scipy
        if scipy_found:
            kdtree = cKDTree(vals)
        else:
            kdtree = None
        image = np.array(self.image)

        rows = image.shape[0]
        
        # We will put neighbors here when we find them
        # These will be the indices to the keys and values...
        neighbors = np.zeros(image.shape[0:2], dtype='intp')

        for i, row in enumerate(image):

            # If we have the kdtree, use it of course
            if kdtree:
                _, neigh = kdtree.query(row, k=1, p=self.minkowski)
            else:
                # Since we don't have the kdtree, we have to
                # brute force find the nearest neighbors...
                # But we don't have to actually find the norms.
                # For a bit of optimization, we don't do the
                # square root at the end.
                neigh = np.zeros(row.shape[0])
                for j, px in enumerate(row):
                    norm_p = np.zeros(vals.shape[0])
                    # TODO maybe we can use a map() here for speed
                    for k, cl in enumerate(vals):
                        norm_p[k] = (cl[0]-px[0])**self.minkowski
                        norm_p[k] += (cl[1]-px[1])**self.minkowski
                        norm_p[k] += (cl[2]-px[2])**self.minkowski
                    neigh[j] = np.argmin(norm_p)

            neighbors[i] = neigh.astype('intp')

        self.neighbors = neighbors
        return neighbors

    def generate_pixelart(self):

        # Creating the final image may take a lot of RAM!
        w = self.texture_width
        h = self.texture_height
        image = np.array(self.image)
        iw = image.shape[0]
        ih = image.shape[1]
        try:
            final = np.zeros((w*iw, h*ih), 3))
        except MemoryError:
            self.logger.critical("Ran out of memory while creating\
                                  final image!")
            return False
        
        for i, row in enumerate(keys[neighbors]):
            for j, key in enumerate(row):
                final[i*w:i*w+w, j*h:j*h+h] = np.array(self.pics[key].copy())
        final = final.astype('intp')
        self.output = Image.fromarray(final)
        return self.output

    def process(self):

        # Test output format
        if not self.is_output_path_valid():
            return False
        # Try to load textures (and filter)
        if not self.load_textures():
            return False
        # Try to load image (and scale)
        if not self.load_image():
            return False

        # We know now that these things are valid.
        # We also assume they won't change during the operation!
        
        # Perform nearest neighbor search
        self.find_nearest_neighbors()
        # Generate pixelart image
        # Save pixelart image
        # Generate report
        # Return report



