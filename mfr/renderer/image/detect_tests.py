import os
import unittest
from nose.tools import *

from .__init__ import ImageRenderer

here, _ = os.path.split(os.path.abspath(__file__))


class TestImage(unittest.TestCase):
    def setUp(self):
        self.renderer = ImageRenderer()

    def test_detect_tif(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.tif'))
        detected = self.renderer.detect(file_pointer)
        assert_true(detected)

    def test_detect_jpg(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.jpg'))
        detected = self.renderer.detect(file_pointer)
        assert_true(detected)

    def test_detect_jpeg(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.jpeg'))
        detected = self.renderer.detect(file_pointer)
        assert_true(detected)

    def test_detect_png(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.png'))
        detected = self.renderer.detect(file_pointer)
        assert_true(detected)

    # Do not detect

    def test_dont_detect_avi(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.avi'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_mp4(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.mp4'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_ogv(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.ogv'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_webm(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.webm'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_wmv(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.wmv'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_pdf(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.pdf'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_csv(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.csv'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_dta(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.dta'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_xlsx(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.xlsx'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_xls(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.xls'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_sav(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.sav'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_scm(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.scm'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_lsl(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.lsl'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_less(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.less'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_Rd(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.Rd'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_abap(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.abap'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_mysql(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.mysql'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_go(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.go'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_ps1(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.ps1'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_Rhtml(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.Rhtml'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_xml(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.xml'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_clj(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.clj'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_ts(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.ts'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_yaml(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.yaml'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_ls(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.ls'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_lp(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.lp'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_ada(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.ada'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_coffee(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.coffee'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_dart(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.dart'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_jack(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.jack'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_bat(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.bat'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_d(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.d'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_lisp(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.lisp'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_glsl(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.glsl'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_cfm(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.cfm'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_xq(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.xq'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_jade(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.jade'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_tex(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.tex'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_soy(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.soy'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_snippets(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.snippets'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_txt(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.txt'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_scala(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.scala'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_pgsql(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.pgsql'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_lua(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.lua'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_rb(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.rb'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_ftl(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.ftl'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_ejs(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.ejs'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_jq(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.jq'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_js(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.js'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_plg(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.plg'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_properties(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.properties'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_asm(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.asm'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_jl(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.jl'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_curly(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.curly'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_sjs(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.sjs'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_space(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.space'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_CBL(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.CBL'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_vbs(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.vbs'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_toml(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.toml'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_logic(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.logic'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_hbs(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.hbs'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_py(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.py'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_ahk(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.ahk'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_cs(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.cs'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_diff(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.diff'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_twig(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.twig'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_java(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.java'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_c9search_results(self):
        file_pointer = open(
            os.path.join(here, 'fixtures/test.c9search_results'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_json(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.json'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_frt(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.frt'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_pl(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.pl'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_matlab(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.matlab'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_tmSnippet(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.tmSnippet'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_hx(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.hx'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_hs(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.hs'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_vm(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.vm'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_groovy(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.groovy'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_md(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.md'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_sass(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.sass'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_mc(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.mc'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_ml(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.ml'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_styl(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.styl'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_lucene(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.lucene'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_r(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.r'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_erb(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.erb'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_v(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.v'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_erl(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.erl'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_vhd(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.vhd'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_ini(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.ini'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_scad(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.scad'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)



    def test_dont_detect_as(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.as'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)


    def test_dont_detect_haml(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.haml'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_pas(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.pas'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_proto(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.proto'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_textile(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.textile'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_html(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.html'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_css(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.css'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_asciidoc(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.asciidoc'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_nix(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.nix'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_jsp(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.jsp'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_sql(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.sql'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_php(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.php'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_jsx(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.jsx'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_scss(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.scss'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_liquid(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.liquid'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_svg(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.svg'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_rs(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.rs'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_m(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.m'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_sh(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.sh'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_cpp(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.cpp'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_tcl(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.tcl'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

    def test_dont_detect_dot(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.dot'))
        detected = self.renderer.detect(file_pointer)
        assert_false(detected)

