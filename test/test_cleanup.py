# -*- coding: utf-8 -*-
"""Tests for the intermediate file cleanup utility."""

import os
import tempfile
import unittest

from geest.core.cleanup import (
    KEEP_EXTENSIONS,
    KEEP_FILENAMES,
    clean_intermediate_files,
)


class TestCleanIntermediateFiles(unittest.TestCase):
    """Test the clean_intermediate_files function."""

    def setUp(self):
        """Create a temporary directory structure mimicking a workflow directory."""
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Remove the temporary directory."""
        import shutil

        shutil.rmtree(self.test_dir, ignore_errors=True)

    def _create_file(self, relative_path, size=100):
        """Helper to create a file with dummy content."""
        full_path = os.path.join(self.test_dir, relative_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "wb") as f:
            f.write(b"x" * size)
        return full_path

    def test_keeps_vrt_files(self):
        """VRT files should be preserved."""
        vrt_path = self._create_file("output_combined.vrt")
        result = clean_intermediate_files(self.test_dir)
        self.assertTrue(os.path.exists(vrt_path))
        self.assertEqual(result["kept_count"], 1)
        self.assertEqual(result["removed_count"], 0)

    def test_keeps_qml_files(self):
        """QML style files should be preserved."""
        qml_path = self._create_file("indicator.qml")
        result = clean_intermediate_files(self.test_dir)
        self.assertTrue(os.path.exists(qml_path))
        self.assertEqual(result["kept_count"], 1)

    def test_keeps_tif_files(self):
        """TIF raster files should be preserved."""
        tif_path = self._create_file("masked_0.tif")
        result = clean_intermediate_files(self.test_dir)
        self.assertTrue(os.path.exists(tif_path))
        self.assertEqual(result["kept_count"], 1)

    def test_keeps_error_txt(self):
        """error.txt should be preserved."""
        err_path = self._create_file("error.txt")
        result = clean_intermediate_files(self.test_dir)
        self.assertTrue(os.path.exists(err_path))
        self.assertEqual(result["kept_count"], 1)

    def test_removes_shapefiles(self):
        """Shapefile components should be removed."""
        for ext in [".shp", ".dbf", ".shx", ".prj", ".cpg"]:
            self._create_file(f"intermediate{ext}")
        result = clean_intermediate_files(self.test_dir)
        self.assertEqual(result["removed_count"], 5)
        self.assertEqual(result["kept_count"], 0)

    def test_removes_gpkg_files(self):
        """GeoPackage intermediate files should be removed."""
        gpkg_path = self._create_file("grid_cells.gpkg")
        result = clean_intermediate_files(self.test_dir)
        self.assertFalse(os.path.exists(gpkg_path))
        self.assertEqual(result["removed_count"], 1)

    def test_recursive_cleanup(self):
        """Files in subdirectories should also be cleaned."""
        self._create_file("subdir/temp_network.gpkg")
        self._create_file("subdir/isochrones.shp")
        self._create_file("subdir/deep/nested.shp")
        result = clean_intermediate_files(self.test_dir)
        self.assertEqual(result["removed_count"], 3)
        # Empty subdirectories should be removed
        self.assertFalse(os.path.exists(os.path.join(self.test_dir, "subdir", "deep")))
        self.assertFalse(os.path.exists(os.path.join(self.test_dir, "subdir")))

    def test_root_directory_preserved(self):
        """The root workflow directory itself should never be removed."""
        self._create_file("temp.shp")
        clean_intermediate_files(self.test_dir)
        self.assertTrue(os.path.isdir(self.test_dir))

    def test_mixed_files(self):
        """A mix of kept and removed files should be handled correctly."""
        self._create_file("output_combined.vrt")
        self._create_file("indicator.qml")
        self._create_file("masked_0.tif", size=1000)
        self._create_file("error.txt")
        self._create_file("grid_cells.gpkg", size=5000)
        self._create_file("intermediate.shp", size=2000)
        self._create_file("intermediate.dbf", size=500)
        result = clean_intermediate_files(self.test_dir)
        self.assertEqual(result["kept_count"], 4)
        self.assertEqual(result["removed_count"], 3)
        self.assertEqual(result["removed_bytes"], 7500)

    def test_nonexistent_directory(self):
        """A nonexistent directory should return empty results without error."""
        result = clean_intermediate_files("/nonexistent/path/to/dir")
        self.assertEqual(result["removed_count"], 0)
        self.assertEqual(result["kept_count"], 0)

    def test_empty_directory(self):
        """An empty directory should return zero counts."""
        result = clean_intermediate_files(self.test_dir)
        self.assertEqual(result["removed_count"], 0)
        self.assertEqual(result["kept_count"], 0)

    def test_case_insensitive_extensions(self):
        """Extension matching should be case-insensitive."""
        tif_upper = self._create_file("output.TIF")
        vrt_upper = self._create_file("output.VRT")
        result = clean_intermediate_files(self.test_dir)
        self.assertTrue(os.path.exists(tif_upper))
        self.assertTrue(os.path.exists(vrt_upper))
        self.assertEqual(result["kept_count"], 2)

    def test_bytes_freed_tracked(self):
        """The total bytes freed should be accurately reported."""
        self._create_file("temp1.gpkg", size=1000)
        self._create_file("temp2.shp", size=2000)
        result = clean_intermediate_files(self.test_dir)
        self.assertEqual(result["removed_bytes"], 3000)


if __name__ == "__main__":
    unittest.main()
