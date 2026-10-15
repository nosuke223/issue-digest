from issue_digest import main


def test_main_runs(capsys):
    main()
    assert capsys.readouterr().out != ""
