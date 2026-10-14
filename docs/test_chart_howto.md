# Как прогнать тестовую картинку через Camera Raw

Картинка: `data/derived/test_chart_srgb16.tif` (2192×1270, 16 бит, sRGB, 222 плашки на сером поле).
Что получится: 8 файлов TIFF (по одному на профиль Color Precision) + 1 контрольный. Я их измерю и сравню с тем, что предсказал мой декодер.
Всё делается в Photoshop. Я не мог проверить эти шаги в самой программе — если меню называется иначе, пришли скриншот.

## 0. Один раз: поставить профили вручную (установщики .app не запускать)
1. В Finder: меню **Переход → Перейти к папке…** (⇧⌘G), вставь `~/Library/Application Support/Adobe/CameraRaw/Settings`. Там уже лежат твои пресеты — это нужная папка.
2. Из `~/Downloads/CP Demo - Lightroom/Profiles/` скопируй **целую папку** `Color Precision Demo - nonRAW` (8 файлов .xmp) в эту Settings.
3. Закрой Photoshop и открой заново — профили подхватываются при запуске.

## 1. Для каждого профиля (8 раз + 1 контрольный)
1. Photoshop: **Файл → Открыть** `test_chart_srgb16.tif`. Если спросит про профиль — «Использовать встроенный». Проверь: **Изображение → Режим** = RGB, 16 бит/канал.
2. **Фильтр → Camera Raw Filter** (⇧⌘A).
3. **Сбросить всё в ноль:** зажми Option — кнопка «Отмена» превратится в «Сбросить», нажми её. Дальше проверь по панели Edit: все ползунки (экспозиция, контраст, света, тени, текстура, чёткость, Dehaze, насыщенность, виньетка, зерно) = 0; Detail → резкость и шумоподавление = 0; Color Mixer и Curve — без правок. Размер, обрезку не трогать.
4. Панель Edit → вверху **Profile** → значок сетки (Browse) → группа **Color Precision Demo - nonRAW** → нужный профиль (названия ниже). Движок **Amount** — 100.
   - Если у Portra после выбора профиля в Color Mixer/Curve появились числа — это нормально, это часть профиля: **не обнулять**. Остальное не трогать.
5. **OK**. Потом **Файл → Сохранить копию** (⌥⌘S): формат **TIFF**, внизу галочки: «Слои» выкл., «ICC-профиль: sRGB» вкл.; в окне параметров TIFF — **16 бит**, сжатие любое (ничего, LZW или ZIP).
6. Имя файла — как в таблице, папка `~/Documents/workspace/10_projects/color_harmony/data/raw/test_chart_out/` (внутри git не попадёт).
7. Закрой изображение **без сохранения** и открой исходный TIFF заново для следующего профиля.

| Профиль в списке Camera Raw | Имя файла |
|---|---|
| (контроль) профиль не выбирать, после сброса просто OK | `cameraraw__control__none.tif` |
| Kodak Portra 400 +0EV Frontier | `cameraraw__Portra400__Frontier.tif` |
| Kodak Portra 400 +0EV Noritsu | `cameraraw__Portra400__Noritsu.tif` |
| Fuji Pro 400H +0EV Frontier | `cameraraw__Pro400H__Frontier.tif` |
| Fuji Pro 400H +0EV Noritsu | `cameraraw__Pro400H__Noritsu.tif` |
| Fuji Velvia 50 +0EV Frontier | `cameraraw__Velvia50__Frontier.tif` |
| Fuji Velvia 50 +0EV Noritsu | `cameraraw__Velvia50__Noritsu.tif` |
| Kodak Gold pushed +0EV Frontier | `cameraraw__GoldPushed__Frontier.tif` |
| Kodak Gold pushed +0EV Noritsu | `cameraraw__GoldPushed__Noritsu.tif` |

Контрольный файл важен: он показывает, меняет ли сам Camera Raw цвет без профиля. Если да — эту поправку вычту из остальных.

## 2. Что дальше (мне)
`python3 -I tools/test_chart/measure_chart.py --out data/derived/test_chart_cameraraw.csv data/raw/test_chart_out` → ΔE2000 между предсказанием и Camera Raw по всем плашкам; критерий: у Gold, Pro 400H, Velvia медиана < 1.
