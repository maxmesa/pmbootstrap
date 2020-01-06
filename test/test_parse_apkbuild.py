"""
Copyright 2020 Oliver Smith

This file is part of pmbootstrap.

pmbootstrap is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

pmbootstrap is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with pmbootstrap.  If not, see <http://www.gnu.org/licenses/>.
"""

import os
import pytest
import sys

# Import from parent directory
pmb_src = os.path.realpath(os.path.join(os.path.dirname(__file__) + "/.."))
sys.path.insert(0, pmb_src)
import pmb.parse._apkbuild


@pytest.fixture
def args(tmpdir, request):
    import pmb.parse
    sys.argv = ["pmbootstrap.py", "init"]
    args = pmb.parse.arguments()
    args.log = args.work + "/log_testsuite.txt"
    pmb.helpers.logging.init(args)
    request.addfinalizer(args.logfd.close)
    return args


def test_subpkgdesc():
    func = pmb.parse._apkbuild.subpkgdesc
    testdata = pmb_src + "/test/testdata"

    # Successful extraction
    path = (testdata + "/init_questions_device/aports/device/"
            "device-nonfree-firmware/APKBUILD")
    pkgdesc = "firmware description"
    assert func(path, "nonfree_firmware") == pkgdesc

    # Can't find the function
    with pytest.raises(RuntimeError) as e:
        func(path, "invalid_function")
    assert str(e.value).startswith("Could not find subpackage function")

    # Can't find the pkgdesc in the function
    path = testdata + "/apkbuild/APKBUILD.missing-pkgdesc-in-subpackage"
    with pytest.raises(RuntimeError) as e:
        func(path, "subpackage")
    assert str(e.value).startswith("Could not find pkgdesc of subpackage")


def test_kernels(args):
    # Kernel hardcoded in depends
    args.aports = pmb_src + "/test/testdata/init_questions_device/aports"
    func = pmb.parse._apkbuild.kernels
    device = "lg-mako"
    assert func(args, device) is None

    # Upstream and downstream kernel
    device = "sony-amami"
    ret = {"downstream": "Downstream description",
           "mainline": "Mainline description"}
    assert func(args, device) == ret


def test_depends_in_depends(args):
    path = pmb_src + "/test/testdata/apkbuild/APKBUILD.depends-in-depends"
    apkbuild = pmb.parse.apkbuild(args, path, check_pkgname=False)
    assert apkbuild["depends"] == ["first", "second", "third"]


def test_parse_attributes():
    # Convenience function for calling the function with a block of text
    def func(attribute, block):
        lines = block.split("\n")
        for i in range(0, len(lines)):
            lines[i] += "\n"
        i = 0
        path = "(testcase in " + __file__ + ")"
        print("=== parsing attribute '" + attribute + "' in test block:")
        print(block)
        print("===")
        return pmb.parse._apkbuild.parse_attribute(attribute, lines, i, path)

    assert func("depends", "pkgname='test'") == (False, None, 0)

    assert func("pkgname", 'pkgname="test"') == (True, "test", 0)

    assert func("pkgname", "pkgname='test'") == (True, "test", 0)

    assert func("pkgname", "pkgname=test") == (True, "test", 0)

    assert func("pkgname", 'pkgname="test\n"') == (True, "test", 1)

    assert func("pkgname", 'pkgname="\ntest\n"') == (True, "test", 2)

    assert func("pkgname", 'pkgname="test" # random comment\npkgrel=3') == \
        (True, "test", 0)

    assert func("depends", "depends='\nfirst\nsecond\nthird\n'#") == \
        (True, "first second third", 4)

    assert func("depends", 'depends="\nfirst\n\tsecond third"') == \
        (True, "first second third", 2)

    assert func("depends", 'depends=') == (True, "", 0)

    with pytest.raises(RuntimeError) as e:
        func("depends", 'depends="\nmissing\nend\nquote\nsign')
    assert str(e.value).startswith("Can't find closing")

    with pytest.raises(RuntimeError) as e:
        func("depends", 'depends="')
    assert str(e.value).startswith("Can't find closing")
