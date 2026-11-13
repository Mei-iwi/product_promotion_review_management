import click
from repositories import shopping_repository as repo


def register_cli(app):
    @app.cli.command('reconcile-promotion-usage')
    def reconcile():
        """Run in maintenance before enabling checkout; never adjusts old stock."""
        if not repo.transaction_supported():
            raise click.ClickException('Cần MongoDB replica set; chưa thay đổi dữ liệu')
        counts = repo.reconcile()
        click.echo('Đã đối soát ' + str(len(counts)) + ' mã; không thay đổi tồn kho đơn cũ.')
